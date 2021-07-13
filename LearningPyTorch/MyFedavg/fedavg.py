# -*- coding:utf-8 -*-
"""
Author: RuiStarlit
File: fedavg
Project: Fedavg
Create Time: 2021-07-07

"""
import os
import copy
import time
import numpy as np
from tqdm import tqdm

import torch

from utils import average_weights, LocalUpdate, get_dataset, test_inference
from models import ResNet18, ResBlock


class Arg:
    def __init__(self):
        self.gpu = 0
        self.num_users = 100
        self.dataset = 'cifar10'
        self.epochs = 10
        self.frac = 0.1
        self.num_classes = 10 if self.dataset == 'cifar10' else 100
        self.local_bs = 10
        self.local_ep = 20
        self.lr = 0.01  # learning rate
        self.optimizer = 'sgd'
        self.verbose = 1
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.trainmodel = 'ResNet18'


args = Arg()

# __main__
start_time = time.time()
# using CPU
torch.cuda.set_device(0)
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# device = 'cpu'
device = args.device
print('deviece:', device)
print('Dataset:', args.dataset)
print('Model:', args.trainmodel)
# global_model = CNNCifar(args)
# if args.trainmodel == 'cifar10':
#     global_model = CNNCifar10(args)

global_model = ResNet18(ResBlock, args)
global_model.to(device)
global_model.train()
print(global_model)
global_weights = global_model.state_dict()
train_dataset, test_dataset, user_groups = get_dataset(args)

# Training
train_loss, train_accuracy = [], []
val_acc_list, net_list = [], []
cv_loss, cv_acc = [], []
print_every = 2
val_loss_pre, counter = 0, 0

for epoch in tqdm(range(args.epochs)):
    local_weights, local_losses = [], []
    print(f'\n | Global Training Round : {epoch + 1} |\n')

    global_model.train()
    m = max(int(args.frac * args.num_users), 1)
    idxs_users = np.random.choice(range(args.num_users), m, replace=False)

    for idx in idxs_users:
        local_model = LocalUpdate(args=args, dataset=train_dataset,
                                  idxs=user_groups[idx])
        w, loss = local_model.update_weights(
            model=copy.deepcopy(global_model), global_round=epoch)
        local_weights.append(copy.deepcopy(w))
        local_losses.append(copy.deepcopy(loss))

    # update global weights
    global_weights = average_weights(local_weights)

    global_model.load_state_dict(global_weights)

    loss_avg = sum(local_losses) / len(local_losses)
    train_loss.append(loss_avg)

    # Calculate avg training accuracy over all users at every epoch
    list_acc, list_loss = [], []
    global_model.eval()
    for c in range(args.num_users):
        local_model = LocalUpdate(args=args, dataset=train_dataset,
                                  idxs=user_groups[idx])
        acc, loss = local_model.inference(model=global_model)
        list_acc.append(acc)
        list_loss.append(loss)
    train_accuracy.append(sum(list_acc) / len(list_acc))

    # print global training loss after every 'i' rounds
    # if (epoch + 1) % print_every == 0:
    if 1 :
        print(f' \nAvg Training Stats after {epoch + 1} global rounds:')
        print(f'Training Loss : {np.mean(np.array(train_loss))}')
        print('Train Accuracy: {:.2f}% \n'.format(100 * train_accuracy[-1]))

# Test inference after completion of training
test_acc, test_loss = test_inference(args, global_model, test_dataset)

print(f' \n Results after {args.epochs} global rounds of training:')
print("|---- Avg Train Accuracy: {:.2f}%".format(100 * train_accuracy[-1]))
print("|---- Test Accuracy: {:.2f}%".format(100 * test_acc))
print('\n Total Run Time: {0:0.4f}'.format(time.time() - start_time))


# PLOTTING (optional)
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

 # Plot Loss curve
plt.figure()
plt.title('Training Loss vs Communication rounds')
plt.plot(range(len(train_loss)), train_loss, color='r')
plt.ylabel('Training loss')
plt.xlabel('Communication Rounds')
# plt.savefig('save/fed_{}_{}_{}_C[{}]_iid[{}]_E[{}]_B[{}]_loss.png'.
#             format(args.dataset, args.model, args.epochs, args.frac,
#                     args.iid, args.local_ep, args.local_bs))
plt.show()

# Plot Average Accuracy vs Communication rounds
plt.figure()
plt.title('Average Accuracy vs Communication rounds')
plt.plot(range(len(train_accuracy)), train_accuracy, color='k')
plt.ylabel('Average Accuracy')
plt.xlabel('Communication Rounds')
# plt.savefig('fed_{}_{}_{}_C[{}]_iid[{}]_E[{}]_B[{}]_acc.png'.
#             format(args.dataset, args.model, args.epochs, args.frac,
#                     args.iid, args.local_ep, args.local_bs))
plt.show()