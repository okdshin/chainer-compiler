from chainer_compiler.elichika.parser import nodes
from chainer_compiler.elichika.parser import values
from chainer_compiler.elichika.parser import functions
from chainer_compiler.elichika.parser import graphs
from chainer_compiler.elichika.parser import utils

import chainer
import chainer.functions as F
import chainer.links as L

def create_return_value_in_chainer_function():
    return values.TensorValue()

def try_get_ref(value, name, lineprop) -> 'values.ValueRef':
    if value is None:
        utils.print_warning('Failed to get value in "{}".'.format(name), lineprop)
        return None

    if isinstance(value, values.Value):
        assert(False)

    if isinstance(value, values.Attribute):
        if value.has_obj():
            return value.get_ref()

    if isinstance(value, values.ValueRef):
        return value

    return None

class ChainerFunction(functions.FunctionBase):
    def __init__(self, func, ret_value_func = create_return_value_in_chainer_function):
        super().__init__()
        self.name = str(func)
        self.args.analyze_args(func)
        self.base_func = func
        self.ret_value_func = ret_value_func

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        funcArgs = self.args.merge_inputs(inst, args)

        node = nodes.NodeCall(self, funcArgs, line)
        graph.add_node(node)
        #value = functions.generate_value_with_same_type(vargs[0])
        value = self.ret_value_func()
        value.name = '@F.{}.{}'.format(line, self.name)
        node.set_outputs([value])
        return values.ValueRef(value)

class CopyFunction(functions.FunctionBase):
    def __init__(self, func):
        super().__init__()
        self.name = str(func)

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        node = nodes.NodeCopy(args.inputs[0].get_value())
        graph.add_node(node)
        ret = functions.generate_copied_value(args.inputs[0].get_value())
        node.set_outputs([ret])
        return values.ValueRef(ret)

class RangeFunction(functions.FunctionBase):
    def __init__(self):
        super().__init__()
        self.name = 'range'

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        node = nodes.NodeGenerate(
            'range', [v.get_value() for v in args.inputs], line)
        graph.add_node(node)
        value = values.RangeValue()
        value.name = '@F.{}.{}'.format(line, self.name)
        node.set_outputs([value])
        return values.ValueRef(value)


class LenFunction(functions.FunctionBase):
    def __init__(self):
        super().__init__()
        self.name = 'len'

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        node = nodes.NodeLen(
            args.inputs[0].get_value(),  # TODO: Check this.
            line
        )
        graph.add_node(node)
        value = values.NumberValue(None)
        value.name = '@F.{}.{}'.format(line, self.name)
        node.set_outputs([value])
        return values.ValueRef(value)


class PrintFunction(functions.FunctionBase):
    def __init__(self):
        super().__init__()
        self.name = 'print'
        self.args.add_arg('self', None)
        self.args.add_arg('v', None)

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        funcArgs = self.args.merge_inputs(inst, args)

        node = nodes.NodeCall(self, funcArgs, line)
        graph.add_node(node)

class ListFunction(functions.FunctionBase):
    def __init__(self):
        super().__init__()
        self.name = 'list'
        self.args.add_arg('value', values.ValueRef(values.NoneValue()))

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        assert(inst is None)

        funcArgs = self.args.merge_inputs(inst, args)
        vargs = funcArgs.get_value().inputs
        value = values.ListValue()

        if isinstance(vargs[0], values.NoneValue):
            node = nodes.NodeGenerate('List', [], line)
            graph.add_node(node)
        else:
            node = nodes.NodeConvert('List', vargs[0], line)
            graph.add_node(node)

        value.name = '@F.{}.{}'.format(line, self.name)
        node.set_outputs([value])
        return values.ValueRef(value)


class AppendFunction(functions.FunctionBase):
    def __init__(self, owner):
        super().__init__()
        self.name = 'append'
        self.owner = owner
        self.args.add_arg('self', None)
        self.args.add_arg('elmnt', None)

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        funcArgs = self.args.merge_inputs(inst, args)

        node = nodes.NodeCall(self, funcArgs, line)

        if inst.in_container:
            raise Exception('Invalid operation')
            
        old_v = inst.get_value()
        new_v = functions.generate_value_with_same_type(old_v)

        # estimate a type contained
        if old_v.has_constant_value():
            new_v.internal_value = list(old_v.internal_value)

        for v in funcArgs.inputs[1:]:
            new_v.append(v)

        # update value
        inst.revise(new_v)

        new_v.name = '@F.{}.{}'.format(line, self.name)
        node.set_outputs([new_v])

        graph.add_node(node)
        return values.NoneValue()


class KeysFunction(functions.FunctionBase):
    def __init__(self, owner):
        super().__init__()
        self.name = 'keys'
        self.owner = owner
        self.args.add_arg('self', None)

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        funcArgs = self.args.merge_inputs(inst, args)

        if inst.in_container:
            raise Exception('Invalid operation')

        keys = inst.get_value().internal_keys.values()

        vargs = []
        vargs_value = []
        for varg in keys:
            vargs.append(try_get_ref(varg, 'keys', utils.LineProperty()))
            vargs_value.append(try_get_ref(varg, 'keys', utils.LineProperty()).get_value())

        node = nodes.NodeGenerate('List', vargs_value , line)
        graph.add_node(node)

        value = values.ListValue(vargs)
        value.name = '@F.{}.{}'.format(line, self.name)
        node.set_outputs([value])
        return value


class ValuesFunction(functions.FunctionBase):
    def __init__(self, owner):
        super().__init__()
        self.name = 'values'
        self.owner = owner
        self.args.add_arg('self', None)

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        funcArgs = self.args.merge_inputs(inst, args)

        if inst.in_container:
            raise Exception('Invalid operation')

        key_hashes = inst.get_value().internal_keys.keys()
        attributes = inst.get_value().internal_values
        vargs = []
        for hash in key_hashes:
            varg = attributes.get_attribute(hash)
            if varg.has_obj():
                vargs.append(varg.get_ref().get_value())
            else:
                assert(False)

        node = nodes.NodeGenerate('List', vargs , line)
        graph.add_node(node)

        value = values.ListValue()
        value.name = '@F.{}.{}'.format(line, self.name)
        node.set_outputs([value])
        return value


class VEvalOptionFunction(functions.FunctionBase):
    def __init__(self, func, flags = None):
        super().__init__()
        self.name = func.__name__
        self.args.analyze_args(func)
        self.flags = flags

    def vcall(self, module: 'Field', graph: 'Graph', inst: 'values.ValueRef', args: 'functions.FunctionArgInput', line=-1):
        assert(inst is None)

        funcArgs = self.args.merge_inputs(inst, args)
        if self.flags is not None:
            self.flags.append(self.name)

        return values.ValueRef(values.NoneValue())