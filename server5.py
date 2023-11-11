from socket import *
from threading import Thread
import sys, select
import datetime
import time
import os
from threading import Lock

# acquire server host and port from command line parameter
if len(sys.argv) != 3:
    print("\n===== Error usage, python3 server.py SERVER_PORT num_times_to_block======\n")
    exit(0)
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])

# check number_of_consecutive_failed_attempts should be an integer
if not sys.argv[2].isdigit():
    print("\n===== Error usage, number_of_consecutive_failed_attempts should be an integer======\n")
    exit(0)
blocked_time = int(sys.argv[2])

# check number_of_consecutive_failed_attempts should be 1 to 5
if blocked_time < 1 or blocked_time > 5:
    print("\n===== Error usage, num_times_to_block should be an integer between 1 and 5, including 1 and 5======\n")
    exit(0)
serverAddress = (serverHost, serverPort)

# define socket for the server side and bind address
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(serverAddress)

# to add user which is blocked
blocked_user = []

# to store the time that a user will be blocked till
end_block_time = {}

client_sockets = {}

groups = {}
# to check if other client is in processing
in_use = False

class ClientThread(Thread):
    def __init__(self, clientAddress, clientSocket):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.loginState = False
        print("===== New connection created for: ", clientAddress)
        
        
    def run(self):
        global blocked_user
        global end_block_time
        global in_use
        global groups
        # initiate message to avoid unexpected error
        message = "ERROR$$"
        # num ber of attempts to log in
        trying = 0
        
        # log in process
        while not self.loginState:
            # receive credentials from client
            data = self.clientSocket.recv(1024)
            
            # record receive time
            current_time = datetime.datetime.now()
            message = data.decode()
            dataType, usernameAndpassword = message.split("$$")
            username, password = usernameAndpassword.split(" ")
            
            # first check if username is still blocked
            if username in blocked_user:
                # if still blocked give response then wait client to send its UDP port number
                # send a close message to its UDP to close it then close connection with client
                if current_time <= end_block_time[username]:
                    message = "ERROR$$In blocked duration"
                    self.clientSocket.send(message.encode())
                    data = self.clientSocket.recv(1024)
                    message = data.decode()
                    dataType, message = message.split("$$")
                    UDPport = int(message)
                    command = "/logout"
                    UDPclientSocket = socket(AF_INET, SOCK_DGRAM)
                    client_IP = list(self.clientAddress)[0]
                    UDPserverAddress = (client_IP, UDPport)
                    UDPclientSocket.sendto(command.encode(), UDPserverAddress)
                    UDPclientSocket.close()
                    break
                # if not blocked now
                # remove username from blocked list
                if current_time > end_block_time[username]:
                    blocked_user.remove(username)
            print(f'> {username} is online')
            # check whether credential is right
            # give response in 3 different conditions:
            # invalid username, invalid password and both right
            # each time, the password is wrong, will increase trying by 1
            with open("credentials.txt") as file:
                message = "ERROR$$Invalid username"
                for line in file:
                    u,p = line.strip().split(" ")
                    if username == u and password == p:
                        message = "SUCCESS$$welcome"
                        self.loginState = True
                        self.login_time = current_time
                        self.username = username
                    elif username == u and password != p:
                        message = "ERROR$$Invalid password"
                        trying += 1
            # when trying reaches 3, the username will be blocked
            if trying == 3:
                message = "ERROR$$blocked"
                self.clientSocket.send(message.encode())
                # add blocke duration to the time receive this credential
                # and save it with its username to a dictionary
                blocked_duration = 10
                blocked_time = current_time + datetime.timedelta(seconds=blocked_duration)
                blocked_user.append(username)
                end_block_time[username] = blocked_time
                # close the client's UDP then disconnect with client side
                data = self.clientSocket.recv(1024)
                message = data.decode()
                dataType, message = message.split("$$")
                UDPport = int(message)
                command = "/logout"
                UDPclientSocket = socket(AF_INET, SOCK_DGRAM)
                client_IP = list(self.clientAddress)[0]
                UDPserverAddress = (client_IP, UDPport)
                UDPclientSocket.sendto(command.encode(), UDPserverAddress)
                UDPclientSocket.close()
                break
            # message here, is the message before 'if trying == 3'
            self.clientSocket.send(message.encode())
            
            # if credential is right, server gave response before and receive UDP port number from client side
            # then upload informations
            if message == "SUCCESS$$welcome":
                data = self.clientSocket.recv(1024)
                message = data.decode()
                dataType, message = message.split("$$")
                self.UDPport = int(message)
                self.login_process()
            
        # when log in    
        while self.loginState:
            client_sockets[self.username] = self.clientSocket
            data = self.clientSocket.recv(1024)
            # after receive a command, first check whether server is processing with other client
            while in_use:
                time.sleep(1)
            
            message = data.decode()
            command_list = message.split(" ")
            command = command_list[0]
            
            # with /logout command
            # send message to client to close its UDP and TCP; print who exit
            if command == "/logout":
                in_use = True
                message = "/logout$$go"
                self.clientSocket.send(message.encode())
                self.logout_process()
                UDPclientSocket = socket(AF_INET, SOCK_DGRAM)
                client_IP = list(self.clientAddress)[0]
                UDPserverAddress = (client_IP, self.UDPport)
                UDPclientSocket.sendto(command.encode(), UDPserverAddress)
                UDPclientSocket.close()
                print(f"> {username} logout")
                self.loginState = False
                in_use = False
            
            elif command == "/activeuser":
                in_use = True
                print(f"> The user {username} issued /activeuser command")
                message = ""
                # check if there is other active user
                with open("userlog.txt", "r") as f:
                    d = f.readlines()
                    for line in d:
                        data_list = line.strip("\n").split("; ")
                        if username == data_list[2]:
                            continue
                        else:
                            other_logintime = data_list[1]
                            other_username = data_list[2]
                            other_IP = data_list[3]
                            other_UDPserverPort = data_list[4]
                            new = other_username+";"+other_IP+";"+other_UDPserverPort+";active since "+other_logintime+"\n"
                            message = message + new
                if message == "":
                    print("> No other active user\nReturn message: no other active user")
                    message = "/activeuser$$no other active user"
                    self.clientSocket.send(message.encode())
                else:
                    message = message[:-1]
                    show = "> Return other active user list:\n"+message
                    message = "/activeuser$$"+message[:-1]
                    print(show)
                    self.clientSocket.send(message.encode())
                in_use = False
            

            elif command == "/msgto":
                in_use = True
                recipient = command_list[1]
                message_content = " ".join(command_list[2:])
                timestamp = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")
                # Append the message to the messagelog.txt file
                with open("messagelog.txt", "a+") as f:
                    # Move to the end of the file to get the last message number
                    f.seek(0, os.SEEK_END)
                    position = f.tell()
                    if position == 0:  # If file is empty, start from message number 1
                        message_number = 1
                    else:
                        f.seek(0)
                        lines = f.readlines()
                        last_line = lines[-1]
                        message_number = int(last_line.split(";")[0]) + 1
                    log_entry = f"{message_number}; {timestamp}; {recipient}; {message_content}\n"
                    f.write(log_entry)

                # Send the message to the recipient if they are online
                if recipient in client_sockets:
                    recipient_socket = client_sockets[recipient]
                    print(f"{username} message to {recipient} \"{message_content}\" at {timestamp}")
                    recipient_message = f"{timestamp}, {self.username}: {message_content}"
                    try:
                        recipient_socket.send(recipient_message.encode())
                        confirmation = f"/msgto$$Message sent at {timestamp}"
                        self.clientSocket.send(confirmation.encode())
                    except:
                        # Handle error if sending fails
                        print(f"Could not send message to {recipient}")
                else:
                    # Handle case where recipient is not connected
                    print(f"User {recipient} is not online.")
                in_use = False
            
            elif command == "/creategroup":
                in_use = True
                print(f"> The user {username} issued /creategroup command")
                group_name = command_list[1]
                if not group_name.isalnum():
                    self.clientSocket.send("ERROR$$Group name must be alphanumeric.".encode())
                elif group_name in groups:
                    self.clientSocket.send(f"ERROR$$Failed to create the group chat {group_name}: group name exists!".encode())
                else:
                    # Create the group with the client as the first member
                    groups[group_name] = {'members': [self.username]}
                    member_list = ' '.join(command_list[2:])
                    groups[group_name]['invited members'] = member_list.split()
                    # Create a log file for the group messages
                    with open(f"{group_name}_messagelog.txt", "w") as f:
                        f.write("")  # Just create the file initially
                    message = "/creategroup$$" + f"Group chat created {group_name}"
                    self.clientSocket.send(message.encode())
                in_use = False

            elif command == "/joingroup":
                in_use = True
                print(f"> The user {username} issued /joingroup command")
                group_name = command_list[1]
                if group_name not in groups:
                    self.clientSocket.send(f"ERROR$$Groupchat {group_name} doesn't exist.".encode())
                elif self.username not in groups[group_name]['invited members']:
                    self.clientSocket.send("ERROR$$Please join the group before sending messages.".encode())
                else:
                    # Add the user to the group's members list
                    groups[group_name]['members'].append(self.username)
                    message = f"/joingroup$$Joined the group chat: {group_name} successfully"
                    self.clientSocket.send(message.encode())
                in_use = False
            

            # Inside the server command processing loop
            elif command == "/groupmsg":
                in_use = True
                print(f"> The user {username} issued /groupmsg command")
                if len(command_list) < 3:
                    self.clientSocket.send("ERROR$$Please provide a group name and a message.".encode())
                else:
                    group_name = command_list[1]
                    message_body = ' '.join(command_list[2:])
                    if group_name not in groups:
                        self.clientSocket.send("ERROR$$The group chat does not exist.".encode())
                    elif self.username not in groups[group_name]['members']:
                        self.clientSocket.send("ERROR$$Please join the group before sending messages.".encode())
                    else:
                        # Append message to log file
                        with open(f"{group_name}_messagelog.txt", "a") as f:
                            message_number = sum(1 for line in open(f"{group_name}_messagelog.txt")) + 1
                            timestamp = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")
                            f.write(f"{message_number}; {timestamp}; {self.username}; {message_body}\n")

                        print(f"{username} issued a message in group chat {group_name}: {timestamp}; {username}; {message_body}")
                        self.clientSocket.send("/groupmsg$$Group chat message sent.".encode())
                        message_to_send = f"/groupmsg$$Group: {group_name}; From: {self.username}; Time: {timestamp}; Message: {message_body}"
                        for member in groups[group_name]['members']:
                            if member != self.username and member in client_sockets:
                                client_sockets[member].send(message_to_send.encode())
                in_use = False


            
            # with /p2pvideo command
            # server will tell client the destination device exists or not
            # and whether it is active
            elif command == "/p2pvideo":
                in_use = True
                aud_username = command_list[1]
                filename = command_list[2]
                valid_username = False
                with open("credentials.txt") as file:
                    for line in file:
                        u,p = line.strip().split(" ")
                        if aud_username == u and username != u:
                            valid_username = True
                if not valid_username:
                    message = "/p2pvideo$$Invalid audience"
                    self.clientSocket.send(message.encode())
                else:
                    message = "/p2pvideo$$not active"
                    with open("userlog.txt", "r") as f:
                        d = f.readlines()
                        for line in d:
                            data_list = line.strip("\n").split("; ")
                            if aud_username == data_list[2]:
                                message = "/p2pvideo$$"+data_list[3]+";"+data_list[4]
                                break
                    self.clientSocket.send(message.encode())
                    #data = self.clientSocket.recv(1024)
                    #message = data.decode()
                    #dataType, message = message.split("$$")
                in_use = False
    
    # log-in process
    # append log-in information to log file; give correct log-in ID 
    def login_process(self):

        current_time = self.login_time.strftime("%d %B %Y %H:%M:%S")
        f = open("userlog.txt", "a")
        f.close()
        with open("userlog.txt", "r") as f:
            d = f.readlines()
            if d == []:
                index = 1
            else:
                index = int(d[-1].strip("\n").split("; ")[0]) + 1
        IP = list(self.clientAddress)[0]
        new = str(index)+"; "+current_time+"; "+self.username+"; "+IP+"; "+str(self.UDPport)+"\n"
        f = open("userlog.txt", "a")
        f.write(f"{new}")
        f.close()
    
    # log-out process
    # delete log-out device and correct other log-in ID
    def logout_process(self):
        global client_sockets
        if self.username in client_sockets:
            del client_sockets[self.username]
        with open("userlog.txt", "r+") as f:
            d = f.readlines()
            number = int(d[-1].strip("\n").split("; ")[0])
            f.seek(0)
            for i in d:
                list_i = i.strip("\n").split("; ")
                if self.username in list_i:
                    number = int(list_i[0])
                if self.username not in list_i:
                    new = i
                    if int(list_i[0]) > number:
                        list_i[0] = str(int(list_i[0]) - 1)
                        new = "; ".join(list_i)
                        new = new + "\n"
                    f.write(new)
            f.truncate()
                
  
print("\n===== Server is running =====")
print("===== Waiting for connection request from clients...=====")


while True:
    serverSocket.listen()
    clientSockt, clientAddress = serverSocket.accept()
    clientThread = ClientThread(clientAddress, clientSockt)
    clientThread.start()
