import talib
import time
import argparse
from flask import Flask, jsonify, request,session, redirect, request, flash,url_for,render_template_string
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
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.base import AdminIndexView,expose
from flask_admin.menu import MenuLink
from werkzeug.security import generate_password_hash, check_password_hash
from flask_babel import Babel
import random
import string