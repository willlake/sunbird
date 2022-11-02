from telnetlib import GA
from typing import OrderedDict
from torch import optim, nn
import pytorch_lightning as pl

from sunbird.models.models import BaseModel
from sunbird.models.loss import GaussianLoglike


class FCN(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.save_hyperparameters()
        n_input = kwargs["n_input"]
        n_output = kwargs["n_output"]
        n_hidden = kwargs["n_hidden"]
        n_layers = kwargs["n_layers"]
        self.learning_rate = kwargs["learning_rate"]
        self.weight_decay = kwargs["weight_decay"]
        act_fn = nn.SiLU()
        model = []
        for layer in range(n_layers):
            if layer == 0:
                n_left = n_input
            else:
                n_left = n_hidden
            model.append((f"mlp{layer}", nn.Linear(n_left, n_hidden)))
            model.append((f"act{layer}", act_fn))
        model.append((f"mlp{layer+1}", nn.Linear(n_hidden, n_output)))
        self.mlp = nn.Sequential(OrderedDict(model))
        if kwargs["loss"] == "gaussian":
            self.loss = GaussianLoglike.from_file()
        elif kwargs["loss"] == "mse":
            self.loss = nn.MSELoss()
        elif kwargs["loss"] == "mae":
            self.loss = nn.L1Loss()

    @staticmethod
    def add_model_specific_args(parent_parser):
        parser = parent_parser.add_argument_group("FCN")
        parser.add_argument("--n_hidden", type=int, default=100)
        parser.add_argument("--n_layers", type=int, default=2)
        parser.add_argument("--learning_rate", type=float, default=0.01)
        parser.add_argument("--weight_decay", type=float, default=0.001)
        parser.add_argument("--loss", type=str, default="mae")
        return parent_parser

    def forward(self, x):
        return self.mlp(x)

    def _compute_loss(self, batch, batch_idx):
        # TODO: it only works with one prediction, adatp
        x, y = batch
        y_pred = self.forward(x)
        return self.loss(y, y_pred)