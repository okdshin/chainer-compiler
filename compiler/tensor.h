#pragma once

#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

#include <absl/types/variant.h>

#include <chainerx/array.h>

#include <common/log.h>
#include <compiler/dtype.h>
#include <compiler/onnx.h>

namespace chainer_compiler {

class Node;

class Tensor {
public:
    explicit Tensor(const onnx::TensorProto& xtensor);
    ~Tensor();

    // Undefined reference indicates the type is not supported yet.
    template <class T>
    Tensor(const std::string& name, Dtype dtype, const std::vector<int64_t>& dims, const std::vector<T>& data);
    template <class T>
    Tensor(const std::string& name, Dtype dtype, const std::vector<int64_t>& dims, const std::initializer_list<T>& data)
        : Tensor(name, dtype, dims, std::vector<T>{data}) {
    }

    Tensor(const Tensor&) = delete;
    Tensor& operator=(const Tensor&) = delete;

    Tensor(const std::string& name, const Tensor& t);
    Tensor(const std::string& name, chainerx::Array ary);

    void ToONNX(onnx::TensorProto* xtensor) const;
    std::string DebugString() const;

    const std::vector<int64_t> dims() const;
    Dtype dtype() const;
    const std::string& name() const {
        return name_;
    }
    const std::string& doc_string() const {
        return doc_string_;
    }

    int ElementSize() const;
    int64_t NumElements() const;

    template <typename T>
    T Get(int index) const {
        CHECK_EQ(dtype().SizeOf(), sizeof(T));
        return static_cast<T*>(chx().raw_data())[index];
    }

    const void* GetRawData() const {
        return chx().raw_data();
    }

    const chainerx::Array& chx() const {
        return absl::get<0>(data_);
    }

    const std::vector<std::string>& str() const {
        return absl::get<1>(data_);
    }

private:
    // Must be a C-contiguous array.
    const absl::variant<chainerx::Array, std::vector<std::string>> data_;
    std::string name_;
    std::string doc_string_;
};

}  // namespace chainer_compiler
