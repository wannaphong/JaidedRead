from .detection import get_detector, get_textbox
from .recognition import get_recognizer, get_text
from .utils import group_text_box, get_image_list
import torch
import urllib.request
import os

MODULE_PATH = os.path.dirname(__file__)

# detector parameters
DETECTOR_PATH = os.path.join(MODULE_PATH, 'model', 'craft_mlt_25k.pth')
text_threshold = 0.7
low_text = 0.4
link_threshold = 0.4
canvas_size = 1280
mag_ratio = 1.5
poly = False

# recognizer parameters
latin_lang_list = ['af','az','bs','cs','cy','da','de','en','es','et','fr','ga','hr','hu','id','is','it','ku',\
            'la','lt','lv','mi','ms','mt','nl','no','pl','pt','ro','sk','sl','sq','sv','sw','tl','tr','uz','vi']
all_lang_list = latin_lang_list + ['th']
imgH = 64
input_channel = 1
output_channel = 512
hidden_size = 512

number = '0123456789'
symbol  = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '

class Reader(object):
    
    def __init__(self, lang_list, gpu = True):
        
        if gpu and torch.cuda.is_available(): self.device = 'cuda'
        else: 
            self.device = 'cpu'
            print('Using cpu, this module is much faster with gpu')
        
        # check available languages
        unknown_lang = set(lang_list) - set(all_lang_list)
        if unknown_lang != set(): 
            raise ValueError(unknown_lang, 'is not supported')
        
        # choose model
        if 'th' in lang_list: 
            model_lang = 'thai'
            if set(lang_list) - set(['th','en']) != set(): 
                raise ValueError('Thai is only compatible with English')  
        else: model_lang = 'latin'
        
        if model_lang == 'latin':
            separator_list = {}
            all_char = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'+\
            'ÀÁÂÃÄÅÆÇÈÉÊËÍÎÑÒÓÔÕÖØÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿąęĮįıŁłŒœŠšųŽž'
            self.character = number+ symbol + all_char
            model_file = 'latin.pth'  

        elif model_lang == 'thai':
            separator_list = {
                'th': ['\xa2', '\xa3'],
                'en': ['\xa4', '\xa5']    
            }
            separator_char = []
            for lang, sep in separator_list.items():
                separator_char += sep

            special_c0 = 'ุู'
            special_c1 = 'ิีืึ'+ 'ั'
            special_c2 = '่้๊๋'
            special_c3 = '็์'
            special_c = special_c0+special_c1+special_c2+special_c3 + 'ำ'
            th_char = 'กขคฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮฤ' +'เแโใไะา'+ special_c +  'ํฺ'+'ฯๆ'
            en_char = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            th_number = '0123456789๑๒๓๔๕๖๗๘๙'
            self.character = ''.join(separator_char) + symbol + en_char + th_char + th_number
            model_file = 'thai.pth'
        else:
            print('invalid language')
        
        dict_list = {}
        for lang in lang_list:
            dict_list[lang] = os.path.join(MODULE_PATH, 'dict', lang + ".txt")

        self.lang_char = []
        for lang in lang_list:
            char_file = os.path.join(MODULE_PATH, 'character', lang + "_char.txt")
            with open(char_file, "r", encoding = "utf-8-sig") as input_file:
                char_list =  input_file.read().splitlines()
            self.lang_char += char_list
        self.lang_char = set(self.lang_char)
        
        MODEL_PATH = os.path.join(MODULE_PATH, 'model', model_file)

        if os.path.isfile(DETECTOR_PATH) == False:
            print('Downloading detection model, please wait')
            urllib.request.urlretrieve('https://jaided.ai/read_download/craft_mlt_25k.pth' , DETECTOR_PATH)
            print('Download complete')

        # check model file
        if os.path.isfile(MODEL_PATH) == False:
            print('Downloading recognition model, please wait')
            urllib.request.urlretrieve('https://jaided.ai/read_download/' + model_file, MODEL_PATH)
            print('Download complete')
            
        self.detector = get_detector(DETECTOR_PATH, self.device)
        self.recognizer, self.converter = get_recognizer(input_channel, output_channel,\
                                                         hidden_size, self.character, separator_list,\
                                                         dict_list, MODEL_PATH, device = self.device)
          
    def readtext(self, file_name, decoder = 'greedy', beamWidth= 5, batch_size = 1, contrast_ths = 0.1,\
                 adjust_contrast = 0.5, filter_ths = 0.003, workers = 1):
        text_box = get_textbox(self.detector, file_name, canvas_size, mag_ratio, text_threshold,\
                               link_threshold, low_text, poly, self.device)
        horizontal_list, free_list = group_text_box(text_box, width_ths = 0.5, add_margin = 0.1)
        
        # should add filter to screen small box out
        
        image_list, max_width = get_image_list(horizontal_list, free_list, file_name, model_height = imgH)
        
        ignore_char = ''.join(set(self.character)-self.lang_char-set(number)-set(symbol))

        result = get_text(self.character, imgH, max_width, self.recognizer, self.converter, image_list,\
                          ignore_char, decoder, beamWidth, batch_size, contrast_ths, adjust_contrast, filter_ths,\
                          workers, self.device)
        return result
