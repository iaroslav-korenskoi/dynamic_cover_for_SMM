#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Deploy on Heroku.com, free plan

import vk_api
import time
from access import yourToken
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

token = yourToken
vk_session = vk_api.VkApi(token=token)
session_api = vk_session.get_api()
load = vk_api.VkUpload(vk_session)
group_id = 'put group ID here'
photo = 'pics/vkcover_ready.png'

def loadOblozhka(i):
    base = Image.open('pics/vkcover_0.jpg').convert('RGBA')        # Take prepared background in RGBA format
    fnt = ImageFont.truetype('fonts/days.ttf', 35)                 # Connect the font
    size = (1590, 400)                                             # Set size of the cover
    time_now = datetime.strftime(datetime.utcnow(), "%H:%M")       # Get current time
    textTime = 'Обложка поменялась в : ' + time_now + ' (UTC)'     # Generate the text
    txt = Image.new('RGBA', size, (255, 255, 255, 0))              # Create empty canvas for the text
    d = ImageDraw.Draw(txt)                                        # Turn text into graphic format
    d.text((680, 40), textTime, font=fnt, fill=(193, 0, 32, 255))  # Concatenate graphic_text with text_canvas
    prep = Image.alpha_composite(base, txt)                        # Concatenate background with text_canvas
    prep.save(photo)                                               # Save final result into graphic file
    load.photo_cover(photo, group_id, 0, 0, 1590, 400)             # Upload final image as social media account's cover 
    time.sleep(120)                                                # Wait 2 minutes before repeat

while True:
    loadOblozhka(0)
