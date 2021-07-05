from transformers import AutoTokenizer, AutoModel
import torch

# load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
model = AutoModel.from_pretrained("allenai/specter")

papers = [
    {
        "title": "DeepWalk: online learning of social representations",
        "abstract": "We present DeepWalk, a novel approach for learning latent representations of vertices in a network. These latent representations encode social relations in a continuous vector space, which is easily exploited by statistical models. DeepWalk generalizes recent advancements in language modeling and unsupervised feature learning (or deep learning) from sequences of words to graphs.DeepWalk uses local information obtained from truncated random walks to learn latent representations by treating walks as the equivalent of sentences. We demonstrate DeepWalk's latent representations on several multi-label network classification tasks for social networks such as BlogCatalog, Flickr, and YouTube. Our results show that DeepWalk outperforms challenging baselines which are allowed a global view of the network, especially in the presence of missing information. DeepWalk's representations can provide F1 scores up to 10% higher than competing methods when labeled data is sparse. In some experiments, DeepWalk's representations are able to outperform all baseline methods while using 60% less training data. DeepWalk is also scalable. It is an online learning algorithm which builds useful incremental results, and is trivially parallelizable. These qualities make it suitable for a broad class of real world applications such as network classification, and anomaly detection.",
    },
    {
        "title": "node2vec: Scalable Feature Learning for Networks",
        "abstract": "Prediction tasks over nodes and edges in networks require careful effort in engineering features used by learning algorithms. Recent research in the broader field of representation learning has led to significant progress in automating prediction by learning the features themselves. However, present feature learning approaches are not expressive enough to capture the diversity of connectivity patterns observed in networks. Here we propose node2vec, an algorithmic framework for learning continuous feature representations for nodes in networks. In node2vec, we learn a mapping of nodes to a low-dimensional space of features that maximizes the likelihood of preserving network neighborhoods of nodes. We define a flexible notion of a node's network neighborhood and design a biased random walk procedure, which efficiently explores diverse neighborhoods. Our algorithm generalizes prior work which is based on rigid notions of network neighborhoods, and we argue that the added flexibility in exploring neighborhoods is the key to learning richer representations. We demonstrate the efficacy of node2vec over existing state-of-the-art techniques on multi-label classification and link prediction in several real-world networks from diverse domains. Taken together, our work represents a new way for efficiently learning state-of-the-art task-independent representations in complex networks.",
    },
    {
        "title": "N2VSCDNNR: A Local Recommender System Based on Node2vec and Rich Information Network",
        "abstract": "Recommender systems are becoming more and more important in our daily lives. However, traditional recommendation methods are challenged by data sparsity and efficiency, as the numbers of users, items, and interactions between the two in many real-world applications increase fast. In this paper, we propose a novel clustering recommender system based on node2vec technology and rich information network, namely, N2VSCDNNR, to solve these challenges. In particular, we use a bipartite network to construct the user-item network and represent the interactions among users (or items) by the corresponding one-mode projection network. In order to alleviate the data sparsity problem, we enrich the network structure according to user and item categories, and construct the one-mode projection category network. Then, considering the data sparsity problem in the network, we employ node2vec to capture the complex latent relationships among users (or items) from the corresponding one-mode projection category network. Moreover, considering the dependence on parameter settings and information loss problem in clustering methods, we use a novel spectral clustering method, which is based on dynamic nearest-neighbors (DNNs) and a novel automatically determining cluster number (ADCN) method that determines the cluster centers based on the normal distribution method, to cluster the users and items separately. After clustering, we propose the two-phase personalized recommendation to realize the personalized recommendation of items for each user. A series of experiments validate the outstanding performance of our N2VSCDNNR over several advanced embedding and side information based recommendation algorithms. Meanwhile, N2VSCDNNR seems to have lower time complexity than the baseline methods in online recommendations, indicating its potential to be widely applied in large-scale systems.",
    },
    {
        "title": "U-Net: Convolutional Networks for Biomedical Image Segmentation",
        "abstract": "There is large consent that successful training of deep networks requires many thousand annotated training samples. In this paper, we present a network and training strategy that relies on the strong use of data augmentation to use the available annotated samples more efficiently. The architecture consists of a contracting path to capture context and a symmetric expanding path that enables precise localization. We show that such a network can be trained end-to-end from very few images and outperforms the prior best method (a sliding-window convolutional network) on the ISBI challenge for segmentation of neuronal structures in electron microscopic stacks. Using the same network trained on transmitted light microscopy images (phase contrast and DIC) we won the ISBI cell tracking challenge 2015 in these categories by a large margin. Moreover, the network is fast. Segmentation of a 512x512 image takes less than a second on a recent GPU. The full implementation (based on Caffe) and the trained networks are available at http://lmb.informatik.uni-freiburg.de/people/ronneber/u-net .",
    },
    {
        "title": "UNet++: A Nested U-Net Architecture for Medical Image Segmentation",
        "abstract": "In this paper, we present UNet++, a new, more powerful architecture for medical image segmentation. Our architecture is essentially a deeply-supervised encoder-decoder network where the encoder and decoder sub-networks are connected through a series of nested, dense skip pathways. The re-designed skip pathways aim at reducing the semantic gap between the feature maps of the encoder and decoder sub-networks. We argue that the optimizer would deal with an easier learning task when the feature maps from the decoder and encoder networks are semantically similar. We have evaluated UNet++ in comparison with U-Net and wide U-Net architectures across multiple medical image segmentation tasks: nodule segmentation in the low-dose CT scans of chest, nuclei segmentation in the microscopy images, liver segmentation in abdominal CT scans, and polyp segmentation in colonoscopy videos. Our experiments demonstrate that UNet++ with deep supervision achieves an average IoU gain of 3.9 and 3.4 points over U-Net and wide U-Net, respectively.",
    },
    {
        "title": "3D U-Net: Learning Dense Volumetric Segmentation from Sparse Annotation",
        "abstract": "This paper introduces a network for volumetric segmentation that learns from sparsely annotated volumetric images. We outline two attractive use cases of this method: (1) In a semi-automated setup, the user annotates some slices in the volume to be segmented. The network learns from these sparse annotations and provides a dense 3D segmentation. (2) In a fully-automated setup, we assume that a representative, sparsely annotated training set exists. Trained on this data set, the network densely segments new volumetric images. The proposed network extends the previous u-net architecture from Ronneberger et al. by replacing all 2D operations with their 3D counterparts. The implementation performs on-the-fly elastic deformations for efficient data augmentation during training. It is trained end-to-end from scratch, i.e., no pre-trained network is required. We test the performance of the proposed method on a complex, highly variable 3D structure, the Xenopus kidney, and achieve good results for both use cases.",
    },
    {
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 Englishto-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.0 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature.",
    },
    {
        "title": "Bert: Pre-training of deep bidirectional transformers for language understanding",
        "abstract": "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers. As a result, the pre-trained BERT model can be fine-tuned with just one additional output layer to create state-of-the-art models for a wide range of tasks, such as question answering and language inference, without substantial task-specific architecture modifications. BERT is conceptually simple and empirically powerful. It obtains new state-of-the-art results on eleven natural language processing tasks, including pushing the GLUE score to 80.5% (7.7% point absolute improvement), MultiNLI accuracy to 86.7% (4.6% absolute improvement), SQuAD v1.1 question answering Test F1 to 93.2 (1.5 point absolute improvement) and SQuAD v2.0 Test F1 to 83.1 (5.1 point absolute improvement).",
    },
]

# concatenate title and abstract
title_abs = [
    d["title"] + tokenizer.sep_token + (d.get("abstract") or "") for d in papers
]
# preprocess the input
inputs = tokenizer(
    title_abs, padding=True, truncation=True, return_tensors="pt", max_length=512
)
result = model(**inputs)
# take the first token in the batch as the embedding
embeddings = result.last_hidden_state[:, 0, :]
cos = torch.nn.CosineSimilarity(dim=0, eps=1e-6)
print(cos(embeddings[0], embeddings[1]))  # 0.9261
print(cos(embeddings[1], embeddings[2]))  # 0.8319
print(cos(embeddings[3], embeddings[4]))  # 0.8732
print(cos(embeddings[3], embeddings[5]))  # 0.8593
print(cos(embeddings[6], embeddings[7]))  # 0.8781
# set the threshold 0.85, and will be evaluated later
