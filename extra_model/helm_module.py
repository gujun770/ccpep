import torch
from transformers import AutoTokenizer, BartForSequenceClassification
from utils.project_paths import HELM_DIR, resolve_model_path
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
tokenizer = AutoTokenizer.from_pretrained(str(HELM_DIR),
                                          ignore_mismatched_sizes=True)
bart = BartForSequenceClassification.from_pretrained(str(HELM_DIR),
                                                     ignore_mismatched_sizes=True)
bart.resize_token_embeddings(len(tokenizer))
bart.load_state_dict(torch.load(
    resolve_model_path('Score_Function', 'Binary', 'Binary-Bart-HELM-fold1.ckpt')))

helm_encoder = bart.model.encoder



















