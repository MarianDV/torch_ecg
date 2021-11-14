"""
"""

import os, sys, time
from typing import NoReturn

import torch
from easydict import EasyDict as ED

try:
    import torch_ecg
except:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import torch_ecg

from torch_ecg.model_configs import (
    # building blocks
    # CNN
    # vgg
    vgg16, vgg16_leadwise,
    # vanilla resnet
    resnet_vanilla_18, resnet_vanilla_34,
    resnet_vanilla_50, resnet_vanilla_101, resnet_vanilla_152,
    resnext_vanilla_50_32x4d, resnext_vanilla_101_32x8d,
    resnet_vanilla_wide_50_2, resnet_vanilla_wide_101_2,
    # custom resnet
    resnet_cpsc2018, resnet_cpsc2018_leadwise,
    # stanford resnet
    resnet_block_stanford, resnet_stanford,
    # cpsc2018 SOTA, legacy
    cpsc_2018, cpsc_2018_leadwise,
    # multi_scopic
    multi_scopic, multi_scopic_leadwise,
    # vanilla dense_net
    dense_net_vanilla,
    # custom dense_net
    dense_net_leadwise,
    # vanilla xception
    xception_vanilla,
    # custom xception
    xception_leadwise,
    # vanilla mobilenets
    mobilenet_v1_vanilla,

    # RNN
    lstm,
    attention,

    # MLP
    linear,

    # ATTN
    non_local,
    squeeze_excitation,
    global_context,


    # downstream tasks
    ATI_CNN_CONFIG,
    ECG_CRNN_CONFIG,
    ECG_SEQ_LAB_NET_CONFIG,
    ECG_SUBTRACT_UNET_CONFIG,
    ECG_UNET_VANILLA_CONFIG,
    ECG_YOLO_CONFIG,
    RR_AF_CRF_CONFIG, RR_AF_VANILLA_CONFIG, RR_LSTM_CONFIG,
)

from torch_ecg.models.cnn.darknet import DarkNet
from torch_ecg.models.cnn.densenet import DenseNet
from torch_ecg.models.cnn.efficientnet import EfficientNet, EfficientNetV2
from torch_ecg.models.cnn.ho_resnet import (
    MidPointResNet, RK4ResNet, RK8ResNet,
)
from torch_ecg.models.cnn.mobilenet import (
    MobileNetV1, MobileNetV2, MobileNetV3,
)
from torch_ecg.models.cnn.multi_scopic import MultiScopicCNN
from torch_ecg.models.cnn.resnet import ResNet
from torch_ecg.models.cnn.vgg import VGG16
from torch_ecg.models.cnn.xception import Xception

from torch_ecg.models.rr_lstm import RR_LSTM
from torch_ecg.models.ecg_crnn import ECG_CRNN
from torch_ecg.models.ecg_seq_lab_net import ECG_SEQ_LAB_NET
from torch_ecg.models.unets.ecg_unet import ECG_UNET
from torch_ecg.models.unets.ecg_subtract_unet import ECG_SUBTRACT_UNET


_DEVICE = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

_IN_CHANNELS = 12
_BATCH_SIZE = 2
_SIG_LEN = 4000
_RR_LEN = 100
_TEST_EXAMPLE = torch.rand((_BATCH_SIZE, _IN_CHANNELS, _SIG_LEN)).to(_DEVICE)
_TEST_RR_EXAMPLE = torch.rand((_RR_LEN, _BATCH_SIZE, 1, )).to(_DEVICE)
_TEST_CLF_CLASSES = ["nsr", "af", "pvc",]
_TEST_DELI_CLASSES = ["qrs", "p", "t",]


@torch.no_grad()
def test_cnn() -> NoReturn:
    """
    """
    start = time.time()
    print("\n"+" Test CNN configs ".center(80,"#")+"\n")
    # test vgg configs
    print("\n"+" Test VGG configs ".center(50,"-")+"\n")
    VGG16.__DEBUG__ = False
    for cfg in ["vgg16", "vgg16_leadwise",]:
        _test_cnn("VGG16", cfg)

    # test resnet configs
    print("\n"+" Test ResNet configs ".center(50,"-")+"\n")
    ResNet.__DEBUG__ = False
    for cfg in [
        "resnet_vanilla_18", "resnet_vanilla_34",
        "resnet_vanilla_50", "resnet_vanilla_101", "resnet_vanilla_152",
        "resnet_vanilla_wide_50_2", "resnet_vanilla_wide_101_2",
        # custom resnet
        "resnet", "resnet_leadwise",
        # TODO: fix bugs in the following
        # "resnext_vanilla_50_32x4d", "resnext_vanilla_101_32x8d",
        # stanford resnet
        # "resnet_stanford",
    ]:
        _test_cnn("ResNet", cfg)

    # test multi_scopic
    print("\n"+" Test MultiScopic configs ".center(50,"-")+"\n")
    MultiScopicCNN.__DEBUG__ = False
    for cfg in ["multi_scopic", "multi_scopic_leadwise",]:
        _test_cnn("MultiScopicCNN", cfg)

    # test densenet
    print("\n"+" Test DenseNet configs ".center(50,"-")+"\n")
    DenseNet.__DEBUG__ = False
    for cfg in ["dense_net_vanilla", "dense_net_leadwise",]:
        _test_cnn("DenseNet", cfg)

    # test xception
    print("\n"+" Test Xception configs ".center(50,"-")+"\n")
    Xception.__DEBUG__ = False
    for cfg in ["xception_vanilla", "xception_leadwise",]:
        _test_cnn("Xception", cfg)

    # test mobilenet
    print("\n"+" Test MobileNet configs ".center(50,"-")+"\n")
    MobileNetV1.__DEBUG__ = False
    MobileNetV2.__DEBUG__ = False
    MobileNetV3.__DEBUG__ = False
    for cfg in ["mobilenet_v1_vanilla",]:
        _test_cnn("MobileNetV1", cfg)

    print(f"total time cost: {time.time()-start:.2f} seconds")
    print("\n"+" Finish testing CNN configs ".center(80,"#")+"\n")

@torch.no_grad()
def _test_cnn(model_name:str, cfg:ED) -> NoReturn:
    """
    """
    try:
        test_model = eval(f"{model_name}(in_channels=_IN_CHANNELS, **{cfg}).to(_DEVICE)")
        test_model.eval()
        test_output = test_model(_TEST_EXAMPLE)
        print(f"{cfg} output shape = {test_output.shape}")
        del test_model
        del test_output
    except Exception as e:
        print(f"{cfg} raises errors\n")
        raise e

@torch.no_grad()
def test_tasks() -> NoReturn:
    """
    """
    start = time.time()
    print("\n"+" Test downstream task configs ".center(80,"#")+"\n")
    # test crnn configs
    print("\n"+" Test ECG_CRNN configs ".center(50,"-")+"\n")
    ECG_CRNN.__DEBUG__ = False
    try:
        test_model = ECG_CRNN(classes=_TEST_CLF_CLASSES, n_leads=_IN_CHANNELS, config=ECG_CRNN_CONFIG).to(_DEVICE)
        test_model.eval()
        test_output = test_model(_TEST_EXAMPLE)
        print(f"ECG_CRNN output shape = {test_output.shape}")
        del test_model
        del test_output
    except Exception as e:
        print("ECG_CRNN_CONFIG raises errors\n")
        raise e

    # test seq_lab configs
    print("\n"+" Test ECG_SEQ_LAB_NET configs ".center(50,"-")+"\n")
    ECG_SEQ_LAB_NET.__DEBUG__ = False
    try:
        test_model = ECG_SEQ_LAB_NET(classes=_TEST_DELI_CLASSES, n_leads=_IN_CHANNELS, config=ECG_SEQ_LAB_NET_CONFIG).to(_DEVICE)
        test_model.eval()
        test_output = test_model(_TEST_EXAMPLE)
        print(f"ECG_SEQ_LAB_NET output shape = {test_output.shape}")
        del test_model
        del test_output
    except Exception as e:
        print("ECG_SEQ_LAB_NET raises errors\n")
        raise e

    # test unet configs
    print("\n"+" Test ECG_UNET configs ".center(50,"-")+"\n")
    ECG_UNET.__DEBUG__ = False
    try:
        test_model = ECG_UNET(classes=_TEST_DELI_CLASSES, n_leads=_IN_CHANNELS, config=ECG_UNET_VANILLA_CONFIG).to(_DEVICE)
        test_model.eval()
        test_output = test_model(_TEST_EXAMPLE)
        print(f"ECG_UNET output shape = {test_output.shape}")
        del test_model
        del test_output
    except Exception as e:
        print("ECG_UNET_VANILLA_CONFIG raises errors\n")
        raise e

    # test subtract_unet configs
    print("\n"+" Test ECG_SUBTRACT_UNET configs ".center(50,"-")+"\n")
    ECG_SUBTRACT_UNET.__DEBUG__ = False
    try:
        test_model = ECG_SUBTRACT_UNET(classes=_TEST_DELI_CLASSES, n_leads=_IN_CHANNELS, config=ECG_SUBTRACT_UNET_CONFIG).to(_DEVICE)
        test_model.eval()
        test_output = test_model(_TEST_EXAMPLE)
        print(f"ECG_SUBTRACT_UNET output shape = {test_output.shape}")
        del test_model
        del test_output
    except Exception as e:
        print("ECG_SUBTRACT_UNET_CONFIG raises errors\n")
        raise e

    # test rr_lstm configs
    print("\n"+" Test RR_LSTM configs ".center(50,"-")+"\n")
    RR_LSTM.__DEBUG__ = False
    for cfg in ["RR_AF_CRF_CONFIG", "RR_AF_VANILLA_CONFIG", "RR_LSTM_CONFIG",]:
        try:
            test_model = eval(f"RR_LSTM(classes=_TEST_CLF_CLASSES, config={cfg}).to(_DEVICE)")
            test_model.eval()
            test_output = test_model(_TEST_RR_EXAMPLE)
            print(f"{cfg} output shape = {test_output.shape}")
            del test_model
            del test_output
        except Exception as e:
            print(f"{cfg} raises errors\n")
            raise e

    print(f"total time cost: {time.time()-start:.2f} seconds")
    print("\n"+" Finish testing downstream task configs ".center(80,"#")+"\n")


def run_test():
    """
    """
    # test CNNs
    test_cnn()
    # test downstream tasks
    test_tasks()


if __name__ == "__main__":
    run_test()
