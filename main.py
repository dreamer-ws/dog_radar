import torch


if __name__ == '__main__':
    a = torch.arange(0, 6)
    a = a.view(2, 3)
    print(a)
    print(a.shape)