from socket import *
from threading import Thread
import time
import sys
import os


def TCP_process(clientSocket, UDPserverPort):
    
    # set loginState to False to initiate it
    loginState = False
    print("> Please login\n")
    # ask for username for the first time
    username = input("> Username: ").strip()
    
    #start login process
    while not loginState:
        # ask for password for the first time
        password = input("> Password: ").strip()
        
        # send the credential to server
        message = "CREDENTIAL$$"+username+" "+password
        clientSocket.send(message.encode())
        
        # reveive response from server,
        # this will tell that credential is credential is right or not
        data = clientSocket.recv(1024)
        receivedMessage = data.decode()
        dataType, receivedMessage = receivedMessage.split("$$")
        
        # the first is just for very special case
        if receivedMessage == "":
            print("> [recv] Message from server is empty!")
        # this means credential is right
        elif receivedMessage == "welcome":
            print("> Welcome to TESSENGER!")
            message = "UDPserverPortNUM$$"+str(UDPserverPort)
            clientSocket.send(message.encode())
            loginState = True
        # this will tell user password is wrong and ask for it agian
        elif receivedMessage == "Invalid password":
            print("> Invalid Password. Please try again")
        # this will tell user username is wrong and ask for it again
        elif receivedMessage == "Invalid username":
            print("> Invalid Username. Please try again")
            username = input("> Username: ").strip()
        # this will tell user, he/she/it/they is blocked and send the UDP port to server
        # for asking shut down this client's UDP and jump to end to close TCP
        elif receivedMessage == 'blocked':
            print("> Invalid Password. Your account has been blocked. Please try again later")
            message = "UDPserverPortNUM$$"+str(UDPserverPort)
            clientSocket.send(message.encode())
            break
        # this will tell user, he/she/it/they is already blocked and send the UDP port to server
        # for asking shut down this client's UDP and jump to end to close TCP
        elif receivedMessage == "In blocked duration":
            print("> Your account is blocked due to multiple authentication failures. Please try again later")
            message = "UDPserverPortNUM$$"+str(UDPserverPort)
            clientSocket.send(message.encode())
            break
            
    # after log in
    while loginState:
        # ask for a COMMAND and give REMINDER
        message = input("> Enter one of the following commands (/msgto, /activeuser, /creategroup, /joingroup, /groupmsg, /p2pvideo, /logout):\n").strip()
        
        # for a correct command, the first is commandtype, them follows argument(s)
        # for each command, the client side will firstly check its format
        command_list = message.split(" ")
        command = command_list[0]
        
        # send logout command to server and wait the response from server then excute
        if command == '/logout':
            if len(command_list) != 1:
                print("> logout command requires no argument.")
            else:
                clientSocket.send(message.encode())
                data = clientSocket.recv(1024)
                message = data.decode()
                dataType, message = message.split("$$")
                if message == "go":
                    print(f"> Bye, {username}!")
                    loginState = False
        
        elif command == "/activeuser":
            if len(command_list) != 1:
                print("> /activeuser command requires no argument.")
            else:
                clientSocket.send(message.encode())
                data = clientSocket.recv(1024)
                message = data.decode()
                dataType, message = message.split("$$")
                if message == "no other active user":
                    print("> no other active users")
                else:
                    print(f"> Other active user:\n{message}")

        # Client code for sending private messages
        elif command == "/msgto":
            if len(command_list) < 3:
                print("> Error: /msgto command requires a username and a message.")
            else:
                clientSocket.send(message.encode())
                data = clientSocket.recv(1024)
                message = data.decode()
                dataType, message = message.split("$$")
                if dataType == "/msgto":
                    print(f"{message}")


        elif command == "/creategroup":
            if len(command_list) < 3:
                print("> Please enter at least one more active users.")
            else:
                # If the group name contains invalid characters, alert the user
                if not command_list[1].isalnum():
                    print("> Error: Group name must be alphanumeric.")
                else:
                    clientSocket.send(message.encode())
                    message = clientSocket.recv(1024).decode()
                    dataType, message = message.split("$$")
                    if dataType == "/creategroup":
                        print("> " + f"{message}")

        elif command == "/joingroup":
            if len(command_list) != 2:  # Require exactly one group name to join
                print("> Error: /joingroup command requires exactly one group name.")
            else:
                clientSocket.send(message.encode())
                # Now, you'll listen for the response from the server and display it
                message = clientSocket.recv(1024).decode()
                dataType, message = message.split("$$")
                if dataType == "/joingroup":
                    print("> " + f"{message}")

        # Inside the client command processing loop
        elif command == "/groupmsg":
            if len(command_list) < 3:
                print("> Error: Please provide a group name and a message.")
            else:
                clientSocket.send(message.encode())
                message = clientSocket.recv(1024).decode()
                dataType, message = message.split("$$")
                if dataType == "/groupmsg":
                    print("> " + f"{message}")


        # send /p2pvideo with arguments to server and wait response from server
        elif command == "/p2pvideo":
            aud_username = command_list[1]
            if len(command_list) != 3:
                print("> Missing username or file name to be uploaded")
            else:
                filename = command_list[2]
                if not os.path.exists(filename):
                    print(f"> No such {filename} file in current directory, please check")
                else:
                    clientSocket.send(message.encode())
                    data = clientSocket.recv(1024)
                    message = data.decode()
                    dataType, message = message.split("$$")
                    if message == "Invalid audience":
                        print("> No such user, please check with command /activeuser")
                    elif message == "not active":
                        print("> such user is not currently active")
                    else:
                        # receive the destination UDP IP and Port number
                        aud_IP, aud_UDPserverPort = message.strip().split(";")
                        # set client UDP here, and send this username and file name
                        # to destination side
                        UDPclientSocket = socket(AF_INET, SOCK_DGRAM)
                        message = "/p2pvideo"+"$$"+username+";"+filename
                        UDPclientSocket.sendto(message.encode(),(aud_IP, int(aud_UDPserverPort)))
                        # wait a few ms to avoid errors
                        time.sleep(0.005)
                        # read file and send data
                        f = open(filename, "rb")
                        data = f.read(1024)
                        packet_num = 1
                        while data:
                            if UDPclientSocket.sendto(data,(aud_IP, int(aud_UDPserverPort))):
                                print(f">>> sending {packet_num}...")
                                data = f.read(1024)
                                packet_num += 1
                                time.sleep(0.005)
                        f.close()
                        UDPclientSocket.sendto("".encode(),(aud_IP, int(aud_UDPserverPort)))
                        UDPclientSocket.close()
                        print(f"> {filename} has been uploaded to {aud_username}")
                        # tell server sending process is done
                        message = "/p2pvideo$$Done"
                        clientSocket.send(message.encode())
        
        # for all other inputs that does not have
        # a correct command
        else:
            print("> Error. Invalid command!")
    
    # close the socket
    clientSocket.close()

# set a keep listening UDP 
def UDP_process(UDPserverSocket, UDPserverAddress):
    while True:
        UDPdata, tuple_ip_port = UDPserverSocket.recvfrom(1024)
        UDPmessage = UDPdata.decode()
        # command to close UDP, will be use when TCP close
        if UDPmessage == "/logout":
            break
        else:
            command, new_filename = UDPmessage.split("$$")
            # doing UVF (peer to peer), this is the audience side
            if command == "/p2pvideo":
                sender_name, old_filename = new_filename.split(";")
                new_filename = sender_name+"_"+old_filename
                # open a new file, and receive packets, then write the data
                f = open(new_filename, "wb")
                UDPdata, tuple_ip_port = UDPserverSocket.recvfrom(1024)
                receive_num = 1
                while UDPdata:
                    print(f">>> receiving {receive_num}...")
                    receive_num += 1
                    f.write(UDPdata)
                    UDPdata, tuple_ip_port = UDPserverSocket.recvfrom(1024)
                f.close
                # open the file in read mode to make file correct
                f = open(new_filename, "r")
                f.close()
                print(f"> Received {old_filename} from {sender_name}")
                # the same with TCP input, while this is end of UDP
                print("> Enter one of the following commands (/msgto, /activeuser, /creategroup, /joingroup, /groupmsg, /p2pvideo, /logout):\n")
                # wait for 1s, to avoid unexpected error
                time.sleep(1)
    
    # close UDP
    UDPserverSocket.close()  
    
def main():
    #Server would be running on the same host as Client
    if len(sys.argv) != 4:
        print("\n===== Error usage, python3 TCPClient3.py SERVER_IP SERVER_PORT ======\n")
        exit(0)
    serverHost = sys.argv[1]
    serverPort = int(sys.argv[2])
    UDPserverPort = int(sys.argv[3])
    serverAddress = (serverHost, serverPort)
    UDPserverAddress = (serverHost, UDPserverPort)

    # define a TCP socket for the client side, it would be used to communicate with the server
    clientSocket = socket(AF_INET, SOCK_STREAM)
    # define a UDP socket as server(audience) side, it would receive data from other peer
    UDPserverSocket = socket(AF_INET, SOCK_DGRAM)

    # build connection with the server and send message to it
    clientSocket.connect(serverAddress)
    # build connection with a specifi UDP address
    UDPserverSocket.bind(UDPserverAddress)
    
    # create TCP thread
    TCP_p = Thread(target=TCP_process, args=(clientSocket, UDPserverPort,))
    TCP_p.start()
    
    # create UDP thread
    UDP_p = Thread(target=UDP_process, args=(UDPserverSocket, UDPserverAddress))
    UDP_p.start()
    
if __name__ == '__main__':
    main()
