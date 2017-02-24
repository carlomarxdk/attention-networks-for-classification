import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.nn.functional as F


def batch_matmul(seq, weight, nonlinearity=''):
    s = None
    for i in range(seq.size(0)):
        _s = torch.mm(seq[i], weight)
        if(nonlinearity=='tanh'):
            _s = torch.tanh(_s)
        _s = _s.unsqueeze(0)
        if(s is None):
            s = _s
        else:
            s = torch.cat((s,_s),0)
    return s.squeeze()


class AttentionWordRNN(nn.Module):
    
    
    def __init__(self, batch_size, num_tokens, embed_size, word_gru_hidden, bidirectional= True):        
        
        super(AttentionWordRNN, self).__init__()
        
        self.batch_size = batch_size
        self.num_tokens = num_tokens
        self.embed_size = embed_size
        self.word_gru_hidden = word_gru_hidden
        self.bidirectional = bidirectional
#         self.max_words = max_words

        
        self.lookup = nn.Embedding(num_tokens, embed_size)
        if bidirectional == True:
            self.word_gru = nn.GRU(embed_size, word_gru_hidden, bidirectional= True)
            self.weight_W_word = nn.Parameter(torch.Tensor(2* word_gru_hidden,2*word_gru_hidden))
#             self.bias_word = nn.Parameter(torch.Tensor(2* word_gru_hidden,1))
            self.weight_proj_word = nn.Parameter(torch.Tensor(2*word_gru_hidden, 1))
        else:
            self.word_gru = nn.GRU(embed_size, word_gru_hidden, bidirectional= False)
            self.weight_W_word = nn.Parameter(torch.Tensor(word_gru_hidden, word_gru_hidden))
#             self.bias_word = nn.Parameter(torch.Tensor(word_gru_hidden,1))
            self.weight_proj_word = nn.Parameter(torch.Tensor(word_gru_hidden, 1))
            
        self.softmax_word = nn.Softmax()
        
        
    def forward(self, embed, state_word):
        # embeddings
        embedded = self.lookup(embed)
#         print embedded.size()
        # word level gru
        output_word, state_word = self.word_gru(embedded, state_word)
#         print output_word.size()
        # word level bat
        word_squish = batch_matmul(output_word, self.weight_W_word, nonlinearity='tanh')
#         print word_squish.size()
        word_attn = batch_matmul(word_squish, self.weight_proj_word)
        word_attn = self.softmax_word(word_attn)
        word_attn_vectors = attention_mul(output_word, word_attn)
#         print word_attn_vectors.size()
        
        return word_attn_vectors
    
    def init_hidden(self):
        if self.bidirectional == True:
            return Variable(torch.zeros(2, self.batch_size, self.word_gru_hidden))
        else:
            return Variable(torch.zeros(1, self.batch_size, self.word_gru_hidden))        
        
        
class AttentionSentRNN(nn.Module):
    
    
    def __init__(self, batch_size, sent_gru_hidden, word_gru_hidden, n_classes, bidirectional= True):        
        
        super(AttentionSentRNN, self).__init__()
        
        self.batch_size = batch_size
        self.sent_gru_hidden = sent_gru_hidden
        self.n_classes = n_classes
        self.word_gru_hidden = word_gru_hidden
        self.bidirectional = bidirectional
        
        
        if bidirectional == True:
            self.sent_gru = nn.GRU(2 * word_gru_hidden, sent_gru_hidden, bidirectional= True)        
            self.weight_W_sent = nn.Parameter(torch.Tensor(2* sent_gru_hidden ,2* sent_gru_hidden))
#             self.bias_sent = nn.Parameter(torch.Tensor(2* sent_gru_hidden,1))
            self.weight_proj_sent = nn.Parameter(torch.Tensor(2* sent_gru_hidden, 1))
            self.final_linear = nn.Linear(2* sent_gru_hidden, n_classes)
        else:
            self.sent_gru = nn.GRU(word_gru_hidden, sent_gru_hidden, bidirectional= True)        
            self.weight_W_sent = nn.Parameter(torch.Tensor(sent_gru_hidden ,sent_gru_hidden))
#             self.bias_sent = nn.Parameter(torch.Tensor(sent_gru_hidden,1))
            self.weight_proj_sent = nn.Parameter(torch.Tensor(sent_gru_hidden, 1))
            self.final_linear = nn.Linear(sent_gru_hidden, n_classes)
        self.softmax_sent = nn.Softmax()
        self.final_softmax = nn.Softmax()
        
    def forward(self, word_attention_vectors, state_sent):
        '''
        Pass a combination of sentence vectors for a batch, I know that this is a little 
        confusing in the beginning, but hold on to it for a while.
        Size word_attention_vectors = sentences_length X batch_size X word_gru_hidden_size
        '''
#         print word_attention_vectors.size()
        # sent level gru
        output_sent, state_sent = self.sent_gru(word_attention_vectors, state_sent)
#         print state_sent.size()
        
        # sent level attention
        sent_squish = batch_matmul(output_sent, self.weight_W_sent ,nonlinearity='tanh')
        sent_attn = batch_matmul(sent_squish, self.weight_proj_sent)
#         print sent_attn.size()
        sent_attn = self.softmax_sent(sent_attn)
        sent_attn_vectors = attention_mul(output_sent, sent_attn)
        
        # final classifier
#         print sent_attn_vectors.squeeze(0).size()
        final_map = self.final_linear(sent_attn_vectors.squeeze(0))
#         final_cls = self.final_softmax(final_map)
        return F.log_softmax(final_map)
    
    def init_hidden(self):
        if self.bidirectional == True:
            return Variable(torch.zeros(2, self.batch_size, self.sent_gru_hidden))
        else:
            return Variable(torch.zeros(1, self.batch_size, self.sent_gru_hidden))   