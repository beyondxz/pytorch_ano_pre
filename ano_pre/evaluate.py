import torch
from Dataset import img_dataset
from models.unet import UNet
import sys
sys.path.append('..')
from torch.utils.data import DataLoader
from losses import *
import numpy as np
from util import psnr_error

import os
import time
import pickle
import eval_metric

training_data_folder='your_path'
testing_data_folder='your_path'

dataset_name='avenue'

psnr_dir='../psnr/'

def evaluate(frame_num, layer_nums, input_channels, output_channels,model_path,evaluate_name,bn=False):
    '''

    :param frame_num:
    :param layer_nums:
    :param input_channels:
    :param output_channels:
    :param model_path:
    :param evaluate_name: compute_auc
    :param bn:
    :return:
    '''
    generator = UNet(n_channels=input_channels, layer_nums=layer_nums, output_channel=output_channels,
                     bn=bn).cuda().eval()

    video_dirs = os.listdir(testing_data_folder)
    video_dirs.sort()

    num_videos = len(video_dirs)
    time_stamp = time.time()

    psnr_records=[]


    total = 0
    generator.load_state_dict(torch.load(model_path))

    for dir in video_dirs:
        _temp_test_folder = os.path.join(testing_data_folder, dir)
        dataset = img_dataset.test_dataset(_temp_test_folder, clip_length=frame_num)

        len_dataset = dataset.pics_len
        test_iters = len_dataset - frame_num + 1
        test_counter = 0

        data_loader = DataLoader(dataset=dataset, batch_size=1, shuffle=False, num_workers=1)

        psnrs = np.empty(shape=(len_dataset,),dtype=np.float32)
        for test_input, _ in data_loader:
            test_target = test_input[:, -1].cuda()
            test_input = test_input[:, :-1].view(test_input.shape[0], -1, test_input.shape[-2],
                                                 test_input.shape[-1]).cuda()

            g_output = generator(test_input)
            test_psnr = psnr_error(g_output, test_target)
            test_psnr = test_psnr.tolist()
            psnrs[test_counter+frame_num-1]=test_psnr

            test_counter += 1
            total+=1
            if test_counter >= test_iters:
                psnrs[:frame_num-1]=psnrs[frame_num-1]
                psnr_records.append(psnrs)
                print('finish test video set {}'.format(_temp_test_folder))
                break

    result_dict = {'dataset': dataset_name, 'psnr': psnr_records, 'flow': [], 'names': [], 'diff_mask': []}

    used_time = time.time() - time_stamp
    print('total time = {}, fps = {}'.format(used_time, total / used_time))

    pickle_path = os.path.join(psnr_dir, os.path.split(model_path)[-1])
    with open(pickle_path, 'wb') as writer:
        pickle.dump(result_dict, writer, pickle.HIGHEST_PROTOCOL)

    results = eval_metric.evaluate(evaluate_name, pickle_path)
    print(results)


if __name__ =='__main__':
    evaluate(frame_num=5,layer_nums=4,input_channels=12,output_channels=3,model_path='../pth_model/ano_pred_avenue_generator.pth-9000',evaluate_name='compute_auc')
