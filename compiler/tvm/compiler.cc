#include "compiler.h"

#include <common/log.h>

#if ONIKU_ENABLE_TVM
#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include <fstream>
#include <string>
#include <vector>

#include <topi/elemwise.h>
#include <topi/nn.h>
#include <topi/cuda/injective.h>
#include <topi/generic/injective.h>
#include <tvm/build_module.h>
#include <tvm/codegen.h>

#include <common/strutil.h>
#include <compiler/flags.h>
#include <compiler/log.h>
#include <compiler/node.h>
#include <compiler/type.h>
#include <compiler/value.h>
#endif

namespace oniku {

#if ONIKU_ENABLE_TVM

namespace {

tvm::Type GetType(Dtype dtype) {
    switch (dtype) {
    case Dtype::kUnknown:
        CHECK(false);
    case Dtype::kBool:
        return tvm::UInt(1);
    case Dtype::kInt8:
        return tvm::Int(8);
    case Dtype::kInt16:
        return tvm::Int(16);
    case Dtype::kInt32:
        return tvm::Int(32);
    case Dtype::kInt64:
        return tvm::Int(64);
    case Dtype::kUInt8:
        return tvm::UInt(8);
    case Dtype::kFloat32:
        return tvm::Float(32);
    case Dtype::kFloat64:
        return tvm::Float(64);
    default:
        CHECK(false) << dtype;
    }
    return tvm::Type();
}

tvm::Array<tvm::Expr> GetShape(const Type& type) {
    CHECK_LT(0, type.NumElements());
    tvm::Array<tvm::Expr> tvm_shape;
    for (int64_t dim : type.dims()) {
        tvm_shape.push_back(tvm::make_const(tvm::Int(32), dim));
    }
    return tvm_shape;
}

tvm::Tensor GetPlaceholder(const Value* value, const std::string& name) {
    return tvm::placeholder(GetShape(value->type()),
                            GetType(value->type().dtype()),
                            name);
}

class TvmCompiler {
public:
    TvmCompiler() {
    }

    ~TvmCompiler() {
    }

    void Build(const std::vector<Node*>& nodes, int id, const std::vector<Value*>& inputs, const std::vector<Value*>& outputs, std::string* filename) {
        PrepareInputs(inputs);

        tvm::Target host{tvm::Target::create("llvm")};
        tvm::Target target;
        if (g_use_cuda) {
            target = tvm::Target{tvm::target::cuda()};
        } else {
            target = host;
        }

        for (Node* node : nodes) {
            std::vector<tvm::Tensor> input_tensors;
            for (Value* input : node->inputs()) {
                auto found = tensors_.find(input);
                CHECK(found != tensors_.end()) << input->DebugString();
                input_tensors.push_back(found->second);
            }

            std::vector<tvm::Tensor> output_tensors;
            if (node->op_type() == Node::kRelu) {
                CHECK_EQ(1, input_tensors.size());
                tvm::Tensor out{topi::relu(input_tensors[0], 0, node->outputs()[0]->name())};
                output_tensors.push_back(out);
            } else if (node->op_type() == Node::kConv) {
                output_tensors.push_back(BuildConv(*node, input_tensors));
            }

            CHECK_EQ(node->outputs().size(), output_tensors.size());
            for (size_t i = 0; i < node->outputs().size(); ++i) {
                CHECK(tensors_.emplace(node->outputs()[i], output_tensors[i]).second);
            }
        }

        std::vector<tvm::Tensor> args;
        std::vector<tvm::Tensor> output_tensors;
        for (Value* output : outputs) {
            auto found = tensors_.find(output);
            CHECK(found != tensors_.end()) << output->DebugString();
            args.push_back(found->second);
            output_tensors.push_back(found->second);
        }
        for (Value* input : inputs) {
            auto found = tensors_.find(input);
            CHECK(found != tensors_.end()) << input->DebugString();
            args.push_back(found->second);
        }

        tvm::Schedule schedule;
        if (g_use_cuda) {
            schedule = topi::cuda::schedule_injective(target, output_tensors);
        } else {
            schedule = topi::generic::schedule_injective(target, output_tensors);
        }

        tvm::BuildConfig config{tvm::build_config()};
        tvm::Array<tvm::LoweredFunc> funcs{tvm::lower(schedule, args, "tvm_op", {}, config)};

        const std::string& dso_name = StrCat("/tmp/liboniku_tvm_op_", id);

        tvm::runtime::Module module = tvm::build(funcs, target, host, config);
        CLOG() << module->type_key() << ": " << module->GetSource() << std::endl;

        std::vector<std::string> input_files;

        const std::string& obj_filename = dso_name + ".o";
        input_files.push_back(obj_filename);
        module->SaveToFile(obj_filename, "o");

        if (g_use_cuda) {
            tvm::runtime::Module& cuda_module = const_cast<tvm::runtime::Module&>(module->imports()[0]);
            CLOG() << cuda_module->type_key() << ": " << cuda_module->GetSource() << std::endl;
            const std::string& dev_filename = dso_name + "_dev.c";
            const std::string& c_code = tvm::codegen::PackImportsToC(module, false /* system_lib */);
            std::ofstream ofs(dev_filename);
            ofs << c_code;
            ofs.close();
            input_files.push_back(dev_filename);
        }

        std::string cmd = StrCat("gcc -shared -fPIC -o ", dso_name, ".so");
        for (const std::string& input_file : input_files) {
            cmd += " " + input_file;
        }
        CLOG() << "Compile: " << cmd << std::endl;
        if (system(cmd.c_str()) != 0) {
            CHECK(false) << strerror(errno) << ": cmd=" << cmd;
        }

        *filename = dso_name + ".so";
    }

private:
    void PrepareInputs(const std::vector<Value*>& inputs) {
        for (Value* input : inputs) {
            tvm::Tensor in{GetPlaceholder(input, input->name())};
            CHECK(tensors_.emplace(input, in).second);
        }
    }

    tvm::Tensor BuildConv(const Node& node, const std::vector<tvm::Tensor>& inputs) {
        CHECK_EQ(2, inputs.size());
        int pad_h = 0, pad_w = 0;
        if (!node.pads().empty()) {
            CHECK_EQ(4, node.pads().size());
            CHECK_EQ(node.pads()[0], node.pads()[2]);
            CHECK_EQ(node.pads()[1], node.pads()[3]);
            pad_w = node.pads()[0];
            pad_h = node.pads()[1];
        }

        int stride_h = 1, stride_w = 1;
        if (!node.strides().empty()) {
            CHECK_EQ(2, node.pads().size());
            stride_w = node.strides()[0];
            stride_h = node.strides()[1];
        }
        tvm::Tensor out{topi::conv2d_nchw(inputs[0], inputs[1], pad_h, pad_w, stride_h, stride_w, node.outputs()[0]->name())};
        return out;
    }

    std::map<Value*, tvm::Tensor> tensors_;
};

}  // namespace

#endif

void BuildTvmProgram(
    const std::vector<Node*>& nodes, int id, const std::vector<Value*>& inputs, const std::vector<Value*>& outputs, std::string* filename) {
#if ONIKU_ENABLE_TVM
    TvmCompiler compiler;
    compiler.Build(nodes, id, inputs, outputs, filename);
#else
    CHECK(false) << "Enable -DONIKU_ENABLE_TVM=ON";
#endif
}

}  // namespace oniku