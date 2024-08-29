from transformers import GPT2LMHeadModel, GPT2Tokenizer, GPT2LMHeadModel, TrainingArguments, Trainer
from datasets import Dataset
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

# Model
model_name = "distilgpt2"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPT2LMHeadModel.from_pretrained(model_name)
model.eval()

# Assigning GPU or CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Promps / Questions
shortPrompts = [
    "Dream tech?",
    "Favorite habit?",
    "Current project?",
    "Best relaxation method?",
    "Top skill?",
    "Most useful habit?",
    "Best recipe?",
    "Favorite blog?",
    "Current trend?",
    "Top tip?",
    "Best movie this year?",
    "Favorite workout?",
    "Favorite place to go?",
    "Best tech purchase?",
    "Ideal hobby?",
    "Best relaxation tip?",
    "Favorite show?",
    "Top food?",
    "Most relaxing activity?",
    "Best weekend plan?",
    "Favorite app feature?",
    "Current favorite hobby?",
    "Best travel destination?",
    "Favorite podcast?",
    "Best tech news?",
    "Top relaxation tip?",
    "Favorite workout routine?",
    "Ideal book?",
    "Best weekend activity?",
    "Favorite social media?",
    "Best app for productivity?",
    "Top habit?",
    "Best way to learn?",
    "Favorite tech?",
    "Best vacation activity?",
    "Most useful skill?",
    "Favorite gadget?",
    "etc...."
]

# Tokenize and pad the text
def tokenize_function(examples):
    encodings = tokenizer(examples['text'], padding='max_length', truncation=True, max_length=80)
    encodings['labels'] = encodings['input_ids']
    return encodings

def trainModel():
    # Create a dataset from the list
    data_dict = {"text": longPrompts}
    dataset = Dataset.from_dict(data_dict)

    # Split dataset into training and validation
    dataset = dataset.train_test_split(test_size=0.1)
    train_dataset = dataset['train']
    eval_dataset = dataset['test']
    tokenizer.pad_token = tokenizer.eos_token

    # Load the model
    model.resize_token_embeddings(len(tokenizer))

    # Tokenize datasets
    tokenized_train_dataset = train_dataset.map(tokenize_function, batched=True)
    tokenized_eval_dataset = eval_dataset.map(tokenize_function, batched=True)
    print(torch.cuda.is_available()) 

    if torch.cuda.is_available():
        model.to('cuda')

    # Define training arguments
    training_args = TrainingArguments(
        output_dir='./gpt2-finetuned',          # Output directory
        per_device_train_batch_size=4,          # Batch size
        num_train_epochs=3,                     # Number of epochs
        logging_dir='./logs',                  # Logging directory
        logging_steps=10,
        save_steps=100,                         # Save model every 500 steps
        save_total_limit=2,                    # Limit to 2 saved models
        evaluation_strategy="epoch",           # Evaluate after each epoch
        weight_decay=0.01,                     # Regularization
        no_cuda=False
    )

    # Initialize the Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_eval_dataset  # Provide eval_dataset
    )

    # Train the model
    trainer.train()
    print(trainer.evaluate())
    
    # Save the model and tokenizer
    model.save_pretrained('./gpt2-finetuned')
    tokenizer.save_pretrained('./gpt2-finetuned')

    # Print an example from the dataset to verify
    print(tokenized_train_dataset[0])

# Generate each indivisual input
def generate_response_title(input_text):
    inputs = tokenizer.encode(input_text, return_tensors='pt').to(device)
    outputs = model.generate(
        inputs,
        max_length=30,             # Max length of the generated sequence
        num_return_sequences=1,       # Number of generated sequences
        temperature=0.7,              # Control randomness (0.7 is a common value)
        top_k=50,                     # Limits the number of highest probability tokens to keep for generation
        top_p=0.95,                   # Nucleus sampling (cumulative probability)
        no_repeat_ngram_size=2,
        pad_token_id=tokenizer.eos_token_id
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

def generate_response_desc(input_text):
    inputs = tokenizer.encode(input_text, return_tensors='pt').to(device)
    outputs = model.generate(
        inputs,
        max_length=70,             # Max length of the generated sequence
        num_return_sequences=1,     # Number of responses to generate
        pad_token_id=tokenizer.eos_token_id,
        do_sample=True,              # Use sampling
        top_p=0.95,                  # Nucleus sampling
        top_k=50                  # Top-k sampling
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response
    
def generateAIComment(listOfTitles, text):
    for x in range(1):
        Title = generate_response_title("awnser this question " + text)
        cleanedUpTitle = Title.replace("awnser this question " + text, "")
        listOfTitles.update({"comment": cleanedUpTitle })

# Generate bunch of inputs
def generateAIPost(listOfTitles):
    for x in range(1):
        grammarOrNot, shortOrLongSentences = random.randint(1,3), random.randint(1,3)
        titleIdea = ""
        
        if shortOrLongSentences == 3: titleIdea = longPrompts[random.randint(0, len(longPrompts)-1)]
        else: titleIdea = shortPrompts[random.randint(0, len(shortPrompts)-1)]

        originalTitle = generate_response_title(titleIdea)
        originalDesc = generate_response_desc(titleIdea)
        cleanedOriginalDesc = originalDesc.replace(titleIdea, "")

        if grammarOrNot == 2 or grammarOrNot == 1: cleanedOriginalDesc = cleanedOriginalDesc.lower(); originalTitle = originalTitle.lower()
        listOfTitles.update({originalTitle: cleanedOriginalDesc})
        print("Added post")

def generateRandomComment(conn, data):
    listOfTitles = {}
    threads = []

    # Generate Comment
    for x in range(random.randint(1,15)):
        t = threading.Thread(target=generateAIComment, args=(listOfTitles,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    print("Added comment")

    jsonData = json.dumps(listOfTitles, indent=4)
    jsonDataEncoded = jsonData.encode('utf-8')
    sizeOfData = struct.pack('!I', len(jsonDataEncoded))
    conn.sendall(sizeOfData + jsonDataEncoded)

def fetchImageUrl(x, y, lock):
    url = f'https://picsum.photos/{x}/{y}'
    response = requests.get(url)
    if response.status_code == 200:
        image_url = str(response.url)
        with lock:
            with open("pfp.txt", "a") as myfile:
                myfile.write(image_url + "\n")
                print("Added image url")

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


def generateRandomTitleAndDesc(conn):
    listOfTitles = {}
    threads = []
    
    for x in range(4):
        t = threading.Thread(target=generateAIPost, args=(listOfTitles,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()

    jsonData = json.dumps(listOfTitles, indent=4)
    jsonDataEncoded = jsonData.encode('utf-8')
    sizeOfData = struct.pack('!I', len(jsonDataEncoded))
    conn.sendall(sizeOfData + jsonDataEncoded)

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
            else:
                generateRandomComment(conn, data.encode('utf-8'))
                print(data.decode('utf-8'))
        except ConnectionResetError:
            print(f"Connection with {addr} was reset")
            break
    
    conn.close()

def start_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()
        print(f"Server listening on {host}:{port}")
        
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()
 
start_server('127.0.0.1', 62131)
