# Imports
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import warnings
import socket
import json
import torch
import threading
import time
import random
import struct
import requests
import asyncio

# Getting AI training Model
model_name = "distilgpt2"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPT2LMHeadModel.from_pretrained(model_name)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# List of inputs
listOfTitlesIdeas = [
    # Casual and Engaging Questions
    "What’s a random fact you know that always surprises people?",
    "If you could instantly learn any skill or talent, what would it be and why?",
    "What’s the most unusual food you’ve ever tried? How was it?",
]

# Generate title
def generate_response_title(input_text):
    inputs = tokenizer.encode(input_text, return_tensors='pt').to(device)
    outputs = model.generate(
        inputs,
        max_length=30,             # Max length of the generated sequence
        num_return_sequences=1,     # Number of responses to generate
        pad_token_id=tokenizer.eos_token_id,
        do_sample=True,              # Use sampling
        top_p=0.95,                  # Nucleus sampling
        top_k=30                  # Top-k sampling
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

# Generate description
def generate_response_desc(input_text):
    inputs = tokenizer.encode(input_text, return_tensors='pt').to(device)
    outputs = model.generate(
        inputs,
        max_length=70,             # Max length of the generated sequence
        num_return_sequences=1,     # Number of responses to generate
        pad_token_id=tokenizer.eos_token_id,
        do_sample=True,              # Use sampling
        top_p=0.95,                  # Nucleus sampling
        top_k=30                  # Top-k sampling
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

# Generating a bunch of posts
def generateAIPost(listOfTitles):
    for x in range(5):
        chosenId = random.randint(0, len(listOfTitlesIdeas)-1)
        grammarOrNot = random.randint(1,3)
        titleIdea = listOfTitlesIdeas[chosenId]

        originalTitle = generate_response_title(titleIdea)
        originalDesc = generate_response_desc(titleIdea)
        cleanedOriginalDesc = originalDesc.replace(originalTitle, "")

        if grammarOrNot == 2 or grammarOrNot == 1: cleanedOriginalDesc = cleanedOriginalDesc.lower(); originalTitle = originalTitle.lower()
        listOfTitles.update({originalTitle: cleanedOriginalDesc})
        
        print("Generated responsed")

# Generating comments
def generateAIComment(listOfTitles, text):
    for x in range(5):
        Title = generate_response_title("awnser this question " + text)
        cleanedUpTitle = Title.replace("awnser this question " + text, "")
        listOfTitles.update({ "comment": cleanedUpTitle })

# Generating a bunch of comments
def generateRandomComment(conn, data):
    listOfTitles = {}
    t1 = threading.Thread(target=generateAIComment, args=(listOfTitles, data))
    t2 = threading.Thread(target=generateAIComment, args=(listOfTitles, data))
    t3 = threading.Thread(target=generateAIComment, args=(listOfTitles, data))
    t4 = threading.Thread(target=generateAIComment, args=(listOfTitles, data))

    t1.start(); t2.start(); t3.start(); t4.start()
    t1.join(); t2.join(); t3.join(); t4.join()

    jsonData = json.dumps(listOfTitles, indent=4)
    jsonDataEncoded = jsonData.encode('utf-8')
    sizeOfData = struct.pack('!I', len(jsonDataEncoded))

    conn.sendall(sizeOfData + jsonDataEncoded)

# Fetching pfp links
def fetchImageUrl(x, y, lock):
    url = f'https://picsum.photos/{x}/{y}'
    response = requests.get(url)
    if response.status_code == 200:
        image_url = str(response.url)
        with lock:
            with open("pfp.txt", "a") as myfile:
                myfile.write(image_url + "\n")
                print("Added ")
              
# Thread system for pfp links
def getImageLinks():
    threads = []
    lock = threading.Lock()

    for _ in range(590):
        x = random.randint(300, 600)
        y = random.randint(300, 600)
        t = threading.Thread(target=fetchImageUrl, args=(x, y, lock))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

# Generate a bunch of posts
def generateRandomTitleAndDesc(conn):
    listOfTitles = {}
    t1 = threading.Thread(target=generateAIPost, args=(listOfTitles,))
    t2 = threading.Thread(target=generateAIPost, args=(listOfTitles,))
    t3 = threading.Thread(target=generateAIPost, args=(listOfTitles,))
    t4 = threading.Thread(target=generateAIPost, args=(listOfTitles,))

    t1.start(); t2.start(); t3.start(); t4.start()
    t1.join(); t2.join(); t3.join(); t4.join()

    jsonData = json.dumps(listOfTitles, indent=4)
    jsonDataEncoded = jsonData.encode('utf-8')
    sizeOfData = struct.pack('!I', len(jsonDataEncoded))
    conn.sendall(sizeOfData + jsonDataEncoded)

# Handle incoming clients thread per connection model
def handle_client(conn, addr):    
    print(f"New connection by {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                print(f"Client {addr} disconnected")
                break
            elif data == b'generate_title_desc\x00':
               generateRandomTitleAndDesc(conn)
            elif data == b'generate_pfp\x00':
               getImageLinks()
        except ConnectionResetError:
            print(f"Connection with {addr} was reset")
            break
    
    conn.close()
  
# Start server
def start_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()
        print(f"Server listening on {host}:{port}")
        
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()
 
start_server('127.0.0.1', 62001)
