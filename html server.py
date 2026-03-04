import socket

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', 12345))
server_socket.listen(1)
print("Server is running on port 12345...")

while True:
    # Accept client connection
    client_connection, client_address = server_socket.accept()
    print(f"Incoming request from {client_address}")
    
    try:
        # Receive the HTTP request
        request = client_connection.recv(1024).decode()
        print(f"Request: {request}")
        
        # Open the file 'index.html'
        try:
            with open("index.html", "r") as f:
                content = f.read()
            
            # Build a proper HTTP/1.1 response
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: " + str(len(content)) + "\r\n\r\n" + content
            
        except FileNotFoundError:
            # If the file is missing, send a 404
            error_content = "<h1>404: File Not Found</h1>"
            response = "HTTP/1.1 404 NOT FOUND\r\nContent-Type: text/html\r\nContent-Length: " + str(len(error_content)) + "\r\n\r\n" + error_content
        
        # Send the response
        client_connection.sendall(response.encode())
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Close the connection
        client_connection.close()
        print("Connection closed.\n")