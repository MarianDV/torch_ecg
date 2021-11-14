"""
configs for the basic cnn layers and blocks
"""
from itertools import repeat
from copy import deepcopy

import numpy as np
from easydict import EasyDict as ED


__all__ = [
    # vgg
    "vgg_block_basic", "vgg_block_mish", "vgg_block_swish",
    "vgg16", "vgg16_leadwise",
    # vanilla resnet
    "resnet_vanilla_18", "resnet_vanilla_34",
    "resnet_vanilla_50", "resnet_vanilla_101", "resnet_vanilla_152",
    "resnext_vanilla_50_32x4d", "resnext_vanilla_101_32x8d",
    "resnet_vanilla_wide_50_2", "resnet_vanilla_wide_101_2",
    # custom resnet
    "resnet_block_basic", "resnet_bottle_neck",
    "resnet_cpsc2018", "resnet_cpsc2018_leadwise",
    # stanford resnet
    "resnet_block_stanford", "resnet_stanford",
    # cpsc2018 SOTA
    "cpsc_block_basic", "cpsc_block_mish", "cpsc_block_swish",
    "cpsc_2018", "cpsc_2018_leadwise",
    # multi_scopic
    "multi_scopic_block",
    "multi_scopic", "multi_scopic_leadwise",
    # vanilla dense_net
    "dense_net_vanilla",
    # custom dense_net
    "dense_net_leadwise",
    # vanilla xception
    "xception_vanilla",
    # custom xception
    "xception_leadwise",
    # vanilla mobilenets
    "mobilenet_v1_vanilla",
]


# VGG
vgg16 = ED()
vgg16.fs = 500
vgg16.num_convs = [2, 2, 3, 3, 3]
_base_num_filters = 12
vgg16.num_filters = [
    _base_num_filters*4,
    _base_num_filters*8,
    _base_num_filters*16,
    _base_num_filters*32,
    _base_num_filters*32,
]
vgg16.groups = 1
vgg16.kernel_initializer = "he_normal"
vgg16.kw_initializer = {}
vgg16.activation = "relu"
vgg16.kw_activation = {}

vgg16_leadwise = deepcopy(vgg16)
vgg16_leadwise.groups = 12
_base_num_filters = 12 * 4
vgg16_leadwise.num_filters = [
    _base_num_filters*4,
    _base_num_filters*8,
    _base_num_filters*16,
    _base_num_filters*32,
    _base_num_filters*32,
]


vgg_block_basic = ED()
vgg_block_basic.filter_length = 15
vgg_block_basic.subsample_length = 1
vgg_block_basic.dilation = 1
vgg_block_basic.batch_norm = True
vgg_block_basic.pool_size = 3
vgg_block_basic.pool_stride = 2  # 2
vgg_block_basic.kernel_initializer = vgg16.kernel_initializer
vgg_block_basic.kw_initializer = deepcopy(vgg16.kw_initializer)
vgg_block_basic.activation = vgg16.activation
vgg_block_basic.kw_activation = deepcopy(vgg16.kw_activation)

vgg_block_mish = deepcopy(vgg_block_basic)
vgg_block_mish.activation = "mish"
del vgg_block_mish.kw_activation

vgg_block_swish = deepcopy(vgg_block_basic)
vgg_block_swish.activation = "swish"
del vgg_block_swish.kw_activation


# set default building block
vgg16.block = deepcopy(vgg_block_basic)
vgg16_leadwise.block = deepcopy(vgg_block_basic)



# ResNet

# vanilla ResNets
resnet_vanilla_common = ED()
resnet_vanilla_common.fs = 500
resnet_vanilla_common.subsample_lengths = [
    1, 2, 2, 2,
]
resnet_vanilla_common.filter_lengths = 15
resnet_vanilla_common.groups = 1
resnet_vanilla_common.increase_channels_method = "conv"
resnet_vanilla_common.init_num_filters = 64
resnet_vanilla_common.init_filter_length = 29
resnet_vanilla_common.init_conv_stride = 2
resnet_vanilla_common.init_pool_size = 3
resnet_vanilla_common.init_pool_stride = 2
resnet_vanilla_common.kernel_initializer = "he_normal"
resnet_vanilla_common.kw_initializer = {}
resnet_vanilla_common.activation = "relu"  # "mish", "swish"
resnet_vanilla_common.kw_activation = {"inplace": True}
resnet_vanilla_common.bias = False
resnet_vanilla_common.block = ED()
resnet_vanilla_common.block.increase_channels_method = "conv"
resnet_vanilla_common.block.subsample_mode = "conv"
resnet_vanilla_common.block.kernel_initializer = resnet_vanilla_common.kernel_initializer
resnet_vanilla_common.block.kw_initializer = deepcopy(resnet_vanilla_common.kw_initializer)
resnet_vanilla_common.block.activation = resnet_vanilla_common.activation
resnet_vanilla_common.block.kw_activation = deepcopy(resnet_vanilla_common.kw_activation)
resnet_vanilla_common.block.bias = False

resnet_vanilla_18 = ED()
resnet_vanilla_18.block_name = "basic"
resnet_vanilla_18.num_blocks = [
    2, 2, 2, 2,
]
resnet_vanilla_18.update(deepcopy(resnet_vanilla_common))
# resnet_vanilla_18.filter_lengths = [
#     list(repeat(3, n)) for n in resnet_vanilla_18.num_blocks
# ]

resnet_vanilla_34 = ED()
resnet_vanilla_34.block_name = "basic"
resnet_vanilla_34.num_blocks = [
    3, 4, 6, 3,
]
resnet_vanilla_34.update(deepcopy(resnet_vanilla_common))
# resnet_vanilla_34.filter_lengths = [
#     list(repeat(3, n)) for n in resnet_vanilla_34.num_blocks
# ]

resnet_vanilla_50 = ED()  # uses bottleneck
resnet_vanilla_50.block_name = "bottleneck"
resnet_vanilla_50.num_blocks = [
    3, 4, 6, 3,
]
resnet_vanilla_50.update(deepcopy(resnet_vanilla_common))
resnet_vanilla_50.base_groups = 1
resnet_vanilla_50.base_width = 64
resnet_vanilla_50.block.subsample_at = 1
resnet_vanilla_50.block.expansion = 4

resnet_vanilla_101 = ED()  # uses bottleneck
resnet_vanilla_101.block_name = "bottleneck"
resnet_vanilla_101.num_blocks = [
    3, 4, 23, 3,
]
resnet_vanilla_101.update(deepcopy(resnet_vanilla_common))
resnet_vanilla_101.base_groups = 1
resnet_vanilla_101.base_width = 64
resnet_vanilla_101.block.subsample_at = 1
resnet_vanilla_101.block.expansion = 4

resnet_vanilla_152 = ED()  # uses bottleneck
resnet_vanilla_152.block_name = "bottleneck"
resnet_vanilla_152.num_blocks = [
    3, 8, 36, 3,
]
resnet_vanilla_152.update(deepcopy(resnet_vanilla_common))
resnet_vanilla_152.base_groups = 1
resnet_vanilla_152.base_width = 64
resnet_vanilla_152.block.subsample_at = 1
resnet_vanilla_152.block.expansion = 4

resnext_vanilla_50_32x4d = ED()  # uses bottleneck
resnext_vanilla_50_32x4d.block_name = "bottleneck"
resnext_vanilla_50_32x4d.num_blocks = [
    3, 4, 6, 3,
]
resnext_vanilla_50_32x4d.update(deepcopy(resnet_vanilla_common))
resnext_vanilla_50_32x4d.groups = 32
resnext_vanilla_50_32x4d.base_groups = 1
resnext_vanilla_50_32x4d.base_width = 4
resnext_vanilla_50_32x4d.block.subsample_at = 1
resnext_vanilla_50_32x4d.block.expansion = 4

resnext_vanilla_101_32x8d = ED()  # uses bottleneck
resnext_vanilla_101_32x8d.block_name = "bottleneck"
resnext_vanilla_101_32x8d.num_blocks = [
    3, 4, 23, 3,
]
resnext_vanilla_101_32x8d.update(deepcopy(resnet_vanilla_common))
resnext_vanilla_101_32x8d.groups = 32
resnext_vanilla_101_32x8d.base_groups = 1
resnext_vanilla_101_32x8d.base_width = 8
resnext_vanilla_101_32x8d.block.subsample_at = 1
resnext_vanilla_101_32x8d.block.expansion = 4

resnet_vanilla_wide_50_2 = ED()  # uses bottleneck
resnet_vanilla_wide_50_2.block_name = "bottleneck"
resnet_vanilla_wide_50_2.num_blocks = [
    3, 4, 6, 3,
]
resnet_vanilla_wide_50_2.update(deepcopy(resnet_vanilla_common))
resnet_vanilla_wide_50_2.base_groups = 1
resnet_vanilla_wide_50_2.base_width = 64 * 2
resnet_vanilla_wide_50_2.block.subsample_at = 1
resnet_vanilla_wide_50_2.block.expansion = 4

resnet_vanilla_wide_101_2 = ED()  # uses bottleneck
resnet_vanilla_wide_101_2.block_name = "bottleneck"
resnet_vanilla_wide_101_2.num_blocks = [
    3, 4, 23, 3,
]
resnet_vanilla_wide_101_2.update(deepcopy(resnet_vanilla_common))
resnet_vanilla_wide_101_2.base_groups = 1
resnet_vanilla_wide_101_2.base_width = 64 * 2
resnet_vanilla_wide_101_2.block.subsample_at = 1
resnet_vanilla_wide_101_2.block.expansion = 4


# custom ResNets
resnet_cpsc2018 = ED()
resnet_cpsc2018.fs = 500
resnet_cpsc2018.block_name = "basic"  # "bottleneck"
resnet_cpsc2018.expansion = 1
resnet_cpsc2018.subsample_lengths = [
    1, 2, 2, 2,
]
# resnet_cpsc2018.num_blocks = [
#     2, 2, 2, 2, 2,
# ]
# resnet_cpsc2018.filter_lengths = 3
# resnet_cpsc2018.num_blocks = [
#     3, 4, 6, 3,
# ]
# resnet_cpsc2018.filter_lengths = [
#     [5, 5, 13],
#     [5, 5, 5, 13],
#     [5, 5, 5, 5, 5, 13],
#     [5, 5, 25],
# ]
resnet_cpsc2018.num_blocks = [
    3, 4, 6, 3,
]
resnet_cpsc2018.filter_lengths = [
    [5, 5, 25],
    [5, 5, 5, 25],
    [5, 5, 5, 5, 5, 25],
    [5, 5, 49],
]
resnet_cpsc2018.groups = 1
_base_num_filters = 12 * 4
resnet_cpsc2018.init_num_filters = _base_num_filters
resnet_cpsc2018.init_filter_length = 15  # corr. to 30 ms
resnet_cpsc2018.init_conv_stride = 2
resnet_cpsc2018.init_pool_size = 3
resnet_cpsc2018.init_pool_stride = 2
resnet_cpsc2018.kernel_initializer = "he_normal"
resnet_cpsc2018.kw_initializer = {}
resnet_cpsc2018.activation = "relu"  # "mish", "swish"
resnet_cpsc2018.kw_activation = {"inplace": True}
resnet_cpsc2018.bias = False


resnet_cpsc2018_leadwise = deepcopy(resnet_cpsc2018)
resnet_cpsc2018_leadwise.groups = 12
resnet_cpsc2018_leadwise.init_num_filters = 12 * 8


resnet_block_basic = ED()
resnet_block_basic.increase_channels_method = "conv"  # or "zero_padding"
resnet_block_basic.subsample_mode = "conv"  # or "max", "avg", "nearest", "linear", "bilinear"
resnet_block_basic.kernel_initializer = resnet_cpsc2018.kernel_initializer
resnet_block_basic.kw_initializer = deepcopy(resnet_cpsc2018.kw_initializer)
resnet_block_basic.activation = resnet_cpsc2018.activation
resnet_block_basic.kw_activation = deepcopy(resnet_cpsc2018.kw_activation)
resnet_block_basic.bias = False

resnet_bottle_neck = ED()
resnet_bottle_neck.expansion = 4
resnet_bottle_neck.increase_channels_method = "conv"  # or "zero_padding"
resnet_bottle_neck.subsample_mode = "conv"  # or "max", "avg", "nearest", "linear", "bilinear"
resnet_bottle_neck.subsample_at = 1  # or 0
resnet_bottle_neck.kernel_initializer = resnet_cpsc2018.kernel_initializer
resnet_bottle_neck.kw_initializer = deepcopy(resnet_cpsc2018.kw_initializer)
resnet_bottle_neck.activation = resnet_cpsc2018.activation
resnet_bottle_neck.kw_activation = deepcopy(resnet_cpsc2018.kw_activation)
resnet_bottle_neck.bias = False


# set default building block
resnet_cpsc2018.block_name = "basic"
resnet_cpsc2018.block = deepcopy(resnet_block_basic)
resnet_cpsc2018_leadwise.block_name = "basic"
resnet_cpsc2018_leadwise.block = deepcopy(resnet_block_basic)



# ResNet Stanford
resnet_stanford = ED()
resnet_stanford.fs = 500
resnet_stanford.groups = 1
resnet_stanford.subsample_lengths = [
    1, 2, 1, 2,
    1, 2, 1, 2,
    1, 2, 1, 2,
    1, 2, 1, 2,
]
resnet_stanford.filter_lengths = 17
_base_num_filters = 36
resnet_stanford.init_num_filters = _base_num_filters*2
resnet_stanford.init_filter_length = 17
resnet_stanford.init_conv_stride = 2
resnet_stanford.init_pool_size = 3
resnet_stanford.init_pool_stride = 2
resnet_stanford.kernel_initializer = "he_normal"
resnet_stanford.kw_initializer = {}
resnet_stanford.activation = "relu"
resnet_stanford.kw_activation = {"inplace": True}
resnet_stanford.bias = False


resnet_block_stanford = ED()
resnet_block_stanford.increase_channels_at = 4
resnet_block_stanford.increase_channels_method = "conv"  # or "zero_padding"
resnet_block_stanford.num_skip = 2
resnet_block_stanford.subsample_mode = "conv"  # "max", "avg"
resnet_block_stanford.kernel_initializer = resnet_stanford.kernel_initializer
resnet_block_stanford.kw_initializer = deepcopy(resnet_stanford.kw_initializer)
resnet_block_stanford.activation = resnet_stanford.activation
resnet_block_stanford.kw_activation = deepcopy(resnet_stanford.kw_activation)
resnet_block_stanford.dropout = 0.2



# CPSC
cpsc_2018 = ED()
cpsc_2018.fs = 500
# cpsc_2018.num_filters = [  # original
#     [12, 12, 12],
#     [12, 12, 12],
#     [12, 12, 12],
#     [12, 12, 12],
#     [12, 12, 12],
# ]
_base_num_filters = 36
cpsc_2018.num_filters = [
    list(repeat(_base_num_filters*2, 3)),
    list(repeat(_base_num_filters*4, 3)),
    list(repeat(_base_num_filters*8, 3)),
    list(repeat(_base_num_filters*16, 3)),
    list(repeat(_base_num_filters*32, 3)),
]
cpsc_2018.filter_lengths = [
    [3, 3, 24],
    [3, 3, 24],
    [3, 3, 24],
    [3, 3, 24],
    [3, 3, 48],
]
cpsc_2018.subsample_lengths = [
    [1, 1, 2],
    [1, 1, 2],
    [1, 1, 2],
    [1, 1, 2],
    [1, 1, 2],
]
cpsc_2018.dropouts = [0.2, 0.2, 0.2, 0.2, 0.2]
cpsc_2018.groups = 1
cpsc_2018.activation = "leaky"
cpsc_2018.kw_activation = ED(negative_slope=0.3, inplace=True)
cpsc_2018.kernel_initializer = "he_normal"
cpsc_2018.kw_initializer = {}

cpsc_2018_leadwise = deepcopy(cpsc_2018)
cpsc_2018_leadwise.groups = 12


cpsc_block_basic = ED()
cpsc_block_basic.activation = cpsc_2018.activation
cpsc_block_basic.kw_activation = deepcopy(cpsc_2018.kw_activation)
cpsc_block_basic.kernel_initializer = cpsc_2018.kernel_initializer
cpsc_block_basic.kw_initializer = deepcopy(cpsc_2018.kw_initializer)
cpsc_block_basic.batch_norm = False

cpsc_block_mish = deepcopy(cpsc_block_basic)
cpsc_block_mish.activation = "mish"
del cpsc_block_mish.kw_activation

cpsc_block_swish = deepcopy(cpsc_block_basic)
cpsc_block_swish.activation = "swish"
del cpsc_block_swish.kw_activation


# TODO: add more

# configs of multi_scopic cnn net are set by path, not by level
multi_scopic = ED()
multi_scopic.fs = 500
multi_scopic.groups = 1
multi_scopic.scopes = [
    [
        [1,],
        [1,1,],
        [1,1,1,],
    ],
    [
        [2,],
        [2,4,],
        [8,8,8,],
    ],
    [
        [4,],
        [4,8,],
        [16,32,64,],
    ],
]
multi_scopic.filter_lengths = [
    [11, 7, 5,],
    [11, 7, 5,],
    [11, 7, 5,],
]
# subsample_lengths for each branch
multi_scopic.subsample_lengths = list(repeat(2, len(multi_scopic.scopes)))
_base_num_filters = 12 * 2
multi_scopic.num_filters = [
    [
        _base_num_filters*4,
        _base_num_filters*8,
        _base_num_filters*16,
    ],
    [
        _base_num_filters*4,
        _base_num_filters*8,
        _base_num_filters*16,
    ],
    [
        _base_num_filters*4,
        _base_num_filters*8,
        _base_num_filters*16,
    ],
]
multi_scopic.dropouts = [
    [0, 0.2, 0],
    [0, 0.2, 0],
    [0, 0.2, 0],
]
multi_scopic.bias = True
multi_scopic.kernel_initializer = "he_normal"
multi_scopic.kw_initializer = {}
multi_scopic.activation = "relu"
multi_scopic.kw_activation = {"inplace": True}
# multi_scopic.batch_norm = False
# multi_scopic.kw_bn = {}

multi_scopic_leadwise = deepcopy(multi_scopic)
multi_scopic_leadwise.groups = 12
# multi_scopic_leadwise.batch_norm = False  # consider using "group_norm"
_base_num_filters = 12 * 4
multi_scopic_leadwise.num_filters = [
    [
        _base_num_filters*4,
        _base_num_filters*8,
        _base_num_filters*16,
    ],
    [
        _base_num_filters*4,
        _base_num_filters*8,
        _base_num_filters*16,
    ],
    [
        _base_num_filters*4,
        _base_num_filters*8,
        _base_num_filters*16,
    ],
]


multi_scopic_block = ED()
multi_scopic_block.subsample_mode = "max"  # or "conv", "avg", "nearest", "linear", "bilinear"
multi_scopic_block.bias = multi_scopic.bias
multi_scopic_block.kernel_initializer = multi_scopic.kernel_initializer
multi_scopic_block.kw_initializer = deepcopy(multi_scopic.kw_initializer)
multi_scopic_block.activation = multi_scopic.activation
multi_scopic_block.kw_activation = deepcopy(multi_scopic.kw_activation)
multi_scopic_block.batch_norm = False  # consider using "group_norm"
multi_scopic_block.kw_bn = {}


# set default building block
multi_scopic.block = deepcopy(multi_scopic_block)
multi_scopic_leadwise.block = deepcopy(multi_scopic_block)



dense_net_vanilla = ED()
dense_net_vanilla.fs = 500
dense_net_vanilla.num_layers = [6, 6, 6, 6]
dense_net_vanilla.init_num_filters = 64
dense_net_vanilla.init_filter_length = 25
dense_net_vanilla.init_pool_stride = 2
dense_net_vanilla.init_pool_size = 3
dense_net_vanilla.init_subsample_mode = "avg"
dense_net_vanilla.growth_rates = 16
dense_net_vanilla.filter_lengths = 15
dense_net_vanilla.subsample_lengths = 2
dense_net_vanilla.bn_size = 4
dense_net_vanilla.dropout = 0
dense_net_vanilla.compression = 0.5
dense_net_vanilla.groups = 1
dense_net_vanilla.block = ED(building_block="basic")
dense_net_vanilla.transition = ED()

dense_net_leadwise = deepcopy(dense_net_vanilla)
dense_net_leadwise.init_num_filters = 12 * 8
dense_net_leadwise.groups = 12



xception_vanilla = ED()
xception_vanilla.fs = 500
xception_vanilla.groups = 1
_base_num_filters = 8
xception_vanilla.entry_flow = ED(
    init_num_filters=[_base_num_filters*4, _base_num_filters*8],
    init_filter_lengths=31,
    init_subsample_lengths=[2,1],
    num_filters=[_base_num_filters*16, _base_num_filters*32, _base_num_filters*91],
    filter_lengths=15,
    subsample_lengths=2,
    subsample_kernels=3,
)
xception_vanilla.middle_flow = ED(
    num_filters=list(repeat(_base_num_filters*91, 8)),
    filter_lengths=13,
)
xception_vanilla.exit_flow = ED(
    final_num_filters=[_base_num_filters*182, _base_num_filters*256],
    final_filter_lengths=3,
    num_filters=[[_base_num_filters*91, _base_num_filters*128]],
    filter_lengths=17,
    subsample_lengths=2,
    subsample_kernels=3,
)

xception_leadwise = ED()
xception_leadwise.fs = 500
xception_leadwise.groups = 12
_base_num_filters = 12 * 2
xception_leadwise.entry_flow = ED(
    init_num_filters=[_base_num_filters*4, _base_num_filters*8],
    init_filter_lengths=31,
    init_subsample_lengths=[2,1],
    num_filters=[_base_num_filters*16, _base_num_filters*32, _base_num_filters*91],
    filter_lengths=15,
    subsample_lengths=2,
    subsample_kernels=3,
)
xception_leadwise.middle_flow = ED(
    num_filters=list(repeat(_base_num_filters*91, 8)),
    filter_lengths=13,
)
xception_leadwise.exit_flow = ED(
    final_num_filters=[_base_num_filters*182, _base_num_filters*256],
    final_filter_lengths=17,
    num_filters=[[_base_num_filters*91, _base_num_filters*128]],
    filter_lengths=3,
    subsample_lengths=2,
    subsample_kernels=3,
)


mobilenet_v1_vanilla = ED()
mobilenet_v1_vanilla.fs = 500
mobilenet_v1_vanilla.groups = 1
mobilenet_v1_vanilla.batch_norm = True
mobilenet_v1_vanilla.activation = "relu6"
mobilenet_v1_vanilla.depth_multiplier = 1  # multiplier of number of depthwise convolution output channels
mobilenet_v1_vanilla.width_multiplier = 1.0  # controls the width (number of filters) of the network
mobilenet_v1_vanilla.bias = True
mobilenet_v1_vanilla.ordering = "cba"

_base_num_filters = 12 * 3
mobilenet_v1_vanilla.init_num_filters = _base_num_filters
mobilenet_v1_vanilla.init_filter_lengths = 27
mobilenet_v1_vanilla.init_subsample_lengths = 2

mobilenet_v1_vanilla.entry_flow = ED()
mobilenet_v1_vanilla.entry_flow.out_channels = [
    # 64, 128, 128, 256, 256
    _base_num_filters * 2,
    _base_num_filters * 4, _base_num_filters * 4,
    _base_num_filters * 8, _base_num_filters * 8,
    _base_num_filters * 16,
]
mobilenet_v1_vanilla.entry_flow.filter_lengths = 15
mobilenet_v1_vanilla.entry_flow.subsample_lengths = [
    1, 2, 1, 2, 1, 2,
]
mobilenet_v1_vanilla.entry_flow.groups = mobilenet_v1_vanilla.groups
mobilenet_v1_vanilla.entry_flow.batch_norm = mobilenet_v1_vanilla.batch_norm
mobilenet_v1_vanilla.entry_flow.activation = mobilenet_v1_vanilla.activation

mobilenet_v1_vanilla.middle_flow = ED()
mobilenet_v1_vanilla.middle_flow.out_channels = list(repeat(_base_num_filters * 16, 5))
mobilenet_v1_vanilla.middle_flow.filter_lengths = 13
mobilenet_v1_vanilla.middle_flow.subsample_lengths = 1
mobilenet_v1_vanilla.middle_flow.groups = mobilenet_v1_vanilla.groups
mobilenet_v1_vanilla.middle_flow.batch_norm = mobilenet_v1_vanilla.batch_norm
mobilenet_v1_vanilla.middle_flow.activation = mobilenet_v1_vanilla.activation

mobilenet_v1_vanilla.exit_flow = ED()
mobilenet_v1_vanilla.exit_flow.out_channels = [
    _base_num_filters * 32, _base_num_filters * 32,
]
mobilenet_v1_vanilla.exit_flow.filter_lengths = 17
mobilenet_v1_vanilla.exit_flow.subsample_lengths = [
    2, 1
]
mobilenet_v1_vanilla.exit_flow.groups = mobilenet_v1_vanilla.groups
mobilenet_v1_vanilla.exit_flow.batch_norm = mobilenet_v1_vanilla.batch_norm
mobilenet_v1_vanilla.exit_flow.activation = mobilenet_v1_vanilla.activation


mobilenet_v2_vanilla = ED()
mobilenet_v2_vanilla.fs = 500
mobilenet_v2_vanilla.groups = 1
mobilenet_v2_vanilla.batch_norm = True
mobilenet_v2_vanilla.activation = "relu6"
mobilenet_v2_vanilla.depth_multiplier = 1  # multiplier of number of depthwise convolution output channels
mobilenet_v2_vanilla.width_multiplier = 1.0  # controls the width (number of filters) of the network
mobilenet_v2_vanilla.bias = True
mobilenet_v2_vanilla.ordering = "cba"

_base_num_filters = 12
mobilenet_v2_vanilla.init_num_filters = _base_num_filters * 4
mobilenet_v2_vanilla.init_filter_lengths = 27
mobilenet_v2_vanilla.init_subsample_lengths = 2

_inverted_residual_setting = np.array([
    # t, c, n, s, k
    [1, _base_num_filters*2, 1, 1, 15],
    [6, _base_num_filters*3, 2, 2, 15],
    [6, _base_num_filters*4, 3, 2, 15],
    [6, _base_num_filters*6, 4, 2, 15],
    [6, _base_num_filters*8, 3, 1, 15],
    [6, _base_num_filters*20, 3, 2, 15],
    [6, _base_num_filters*40, 1, 1, 15],
    # t: expansion
    # c: output channels
    # n: number of blocks
    # s: stride
    # k: kernel size
])
mobilenet_v2_vanilla.inv_res = ED()
mobilenet_v2_vanilla.inv_res.expansions = _inverted_residual_setting[...,0]
mobilenet_v2_vanilla.inv_res.out_channels = _inverted_residual_setting[...,1]
mobilenet_v2_vanilla.inv_res.n_blocks = _inverted_residual_setting[...,2]
mobilenet_v2_vanilla.inv_res.strides = _inverted_residual_setting[...,3]
mobilenet_v2_vanilla.inv_res.filter_lengths = _inverted_residual_setting[...,4]

mobilenet_v2_vanilla.final_num_filters = _base_num_filters * 128
mobilenet_v2_vanilla.final_filter_lengths = 19
mobilenet_v2_vanilla.final_subsample_lengths = 2
