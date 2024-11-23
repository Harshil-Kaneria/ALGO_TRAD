import talib
import time
import argparse
from flask import Flask, jsonify, request
from flask_cors import CORS
from kite_trade import *
import os
from datetime import datetime, timedelta,date
import yfinance as yf
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv
from transformers import pipeline
import requests
from bs4 import BeautifulSoup
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LinearRegression
from typing import Dict
import re
import pyotp
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64
import json