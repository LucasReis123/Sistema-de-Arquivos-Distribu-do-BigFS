import socket
import threading
import traceback
import shutil
import glob
import os

class Server:

    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port

        usuario = os.getlogin()
        self.base_dir = os.path.join("/home", usuario, "tmp/SERVER")

        if not os.path.exists(self.base_dir):
            os.makedirs(os.path.expanduser(self.base_dir), exist_ok=True)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IPv4 e TCP
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.client_ids = 0
        print(f"Servidor aguardando conexões em {self.host}:{self.port}...")

    def handle_client(self, conn, addr):
        print(f"Nova conexão de {addr}")
        id = self.client_ids
        self.client_ids += 1

        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break

                try:
                    response = None
                    message = data.decode()

                    parts = message.split()
                    command = parts[0].strip().strip('"')
                    args = [arg.strip().strip('"') for arg in parts[1:]]

                    # Comando apra listar arquivos em um diretório
                    if command in ['listar', 'ls']:
                        response = self.listar(args)
                        
                    elif command in ['copy', 'cp']:
                        response = self.copy(conn, args)

                    elif command in ['get', 'baixar']:
                        filename = args[0]
                        self.baixar(filename, conn)
                        continue

                    elif command in ['remover', 'rm']:
                        response = self.remover(args)

                    elif command == "exit":
                        response = "Conexão encerrada pelo cliente."
                        conn.sendall(response.encode())
                        break

                except Exception as e:
                    response = f"Erro: {str(e)}"
                    print("Exceção capturada:")
                    traceback.print_exc()

                    response = "Erro: Comando invalido ou argumentos incorretos."


                conn.sendall(response.encode())

            except ConnectionResetError:
                break

        print(f"Conexão encerrada com {addr}")
        conn.close()

    def start(self):
        while True:
            conn, addr = self.server_socket.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

    def abs_path(self, path=""):
        """Retorna o caminho absoluto dentro da pasta tmp"""
        return os.path.abspath(os.path.join(self.base_dir, path))

    def listar(self, args):

        # Listar arquivos no diretório atual
        if len(args) == 0:
            dir = self.abs_path()
            files = os.listdir(dir)
            response = '\n'.join(files) if files else ' '

        # Listar arquivos em um diretório específico
        elif len(args) == 1:
            dir = self.abs_path(args[0])
            try:
                files = os.listdir(f"{dir}")
                response = '\n'.join(files)

            except FileNotFoundError:
                response = "Diretório não encontrado"
            except NotADirectoryError:
                    response = f"Erro: '{args[0]}' não é um diretório\n"

        
        # Agumentos inválidos
        else:
            response = "Argumentos Errados"

        return response

    def copy(self, conn, args):
        if len(args) != 2:
            conn.sendall(b"Uso correto: copy <filename> <destino>")
            return

        filename, destino = args
        destino_dir = os.path.join(self.base_dir, destino)
        os.makedirs(destino_dir, exist_ok=True)

        file_path = os.path.join(destino_dir, os.path.basename(filename))

        if os.path.exists(file_path):
            return f"Erro: O arquivo '{file_path}' já existe."

        # Envia confirmação para o cliente
        conn.sendall(b"ok")
        with open(file_path, "wb") as f:
            while True:
                chunk = conn.recv(4096)
                if b"<EOF>" in chunk:
                    chunk = chunk.replace(b"<EOF>", b"")
                    f.write(chunk)
                    break
                f.write(chunk)

        return "done"
    
    def baixar(self, filename, conn):
        filepath = self.abs_path(filename)

        if not os.path.exists(filepath):
            response = f"Erro: Arquivo '{filename}' não encontrado."
            conn.sendall(response.encode())
            return

        # Arquivo existe: avisa o cliente que está pronto para enviar
        response = f"Pronto para enviar o arquivo '{filename}'"
        conn.sendall(response.encode())

        # Aguarda confirmação do cliente para iniciar envio
        confirm = conn.recv(1024).decode().strip()
        if confirm != "ok":
            return

        # Envia o conteúdo do arquivo em partes
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                conn.sendall(chunk)

        # Envia um marcador de fim de arquivo
        conn.sendall(b"<EOF>")
        return

    
    def remover(self, args):
        path = self.abs_path(args[0])
        paths = glob.glob(path)

        if not paths:
            response = f"Erro: '{path}' não encontrado."
        else:
            for p in paths:
                try:
                    os.remove(p) if os.path.isfile(p) else shutil.rmtree(p)

                except Exception:
                    continue

            response = f"Remoção de {len(paths)} item(ns) concluída."
        
        return response


if __name__ == "__main__":
    server = Server()
    server.start()
