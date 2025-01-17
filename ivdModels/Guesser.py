import torch
import torch.autograd as autograd
import torch.nn as nn
from torch.autograd import Variable
import torch.nn.functional as F

use_cuda = torch.cuda.is_available()
# use_cuda = False

class Guesser(nn.Module):

    def __init__(self, hidden_encoder_dim, categories_length, cat2id, object_embedding_dim):
        """
        Parameters
        hidden_encoder_dim          Dimensionality of the hidden state of the encoder
        categories_length           Number of object categories_length
        cat2id                      Dictionary to convert a category into an id
        object_embedding_dim        Dimensionality of the object embeddings
        """
        super(Guesser, self).__init__()


        self.spatial_dim = 8
        self.categories_length = categories_length
        self.object_embedding_dim = object_embedding_dim
        self.hidden_encoder_dim = hidden_encoder_dim
        self.cat2id = cat2id

        self.object_embeddings = nn.Embedding(self.categories_length, self.object_embedding_dim)

        self.mlp_model = nn.Sequential(
            nn.Linear(self.object_embedding_dim + self.spatial_dim, 64),
            nn.ReLU(),
            nn.Linear(64, self.hidden_encoder_dim)
        )
        if use_cuda:
            self.mlp_model.cuda()


    def get_cat2id(self, cat):
        onehot = torch.zeros(self.categories_length)
        onehot[self.cat2id[cat]] = 1
        return onehot


    def img_spatial(self, img_meta):
        """ returns the spatial information of a bounding box """
        bboxes          = img_meta[0] # gets all bboxes in the image

        width           = img_meta[1]
        height          = img_meta[2]

        image_center_x  = width / 2
        image_center_y  = height / 2

        
        spatial = torch.FloatTensor(len(bboxes), 8)

        for i, bbox in enumerate(bboxes):
            x_min = bbox[0] / width
            y_min = bbox[1] / height
            x_max = (bbox[0] + bbox[2]) / width
            y_max = (bbox[1] + bbox[3]) / height


            w_box = x_max - x_min
            h_box = y_max - y_min

            x_min = x_min * 2 - 1
            y_min = y_min * 2 - 1
            x_max = x_max * 2 - 1
            y_max = y_max * 2 - 1


            x_center = (x_min + x_max) / 2
            y_center = (y_min + y_max) / 2


            spatial[i] = torch.FloatTensor([x_min, y_min, x_max, y_max, x_center, y_center, w_box, h_box])


        return spatial


    def forward(self, hidden_encoder, spatial, object_categories):

        # get the object embeddings of the objects in the image
        if use_cuda:
            obj_embeddings = self.object_embeddings(Variable(object_categories).cuda())
        else:
            obj_embeddings = self.object_embeddings(Variable(object_categories))

        # get the spatial info
        # spatial = self.img_spatial(img_meta)

        mlp_in = torch.cat([spatial, obj_embeddings], dim=1)


        proposed_embeddings = self.mlp_model(mlp_in)

        hidden_encoder = torch.cat([hidden_encoder[0]] * len(object_categories))

        return F.log_softmax(torch.mm(proposed_embeddings, hidden_encoder[0].view(self.hidden_encoder_dim, -1)).t())
