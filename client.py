import socket
import os
from time import sleep

class Client:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.client_socket.connect((self.host, self.port))
        print("Conectado ao servidor. Digite 'help' para ver os comandos disponíveis.\n")

        while True:
            cmd = input(":$ ").strip()

            if not cmd:
                continue

            parts = cmd.split()
            command = parts[0]
            args = parts[1:]

            if command in ['listar', 'ls']:
                msg = cmd

            elif command in ['copy', 'cp']:
                self.copy(args)
                continue

            elif command in ['get', 'baixar']:
                self.get(args)
                continue


            elif command in ['remover', 'rm']:
                if len(args) != 1:
                    print("Uso correto: rm <arquivo_ou_diretorio>")
                    continue

                msg = cmd

            elif command == "exit":
                msg = cmd
                self.client_socket.sendall(msg.encode())
                response = self.client_socket.recv(4096)
                print(response.decode())
                break

            elif command == "clear":
                print("\033[H\033[J", end="")
                continue

            elif command == "help":
                if len(args) == 0:
                    self.help()
                    continue
                
                print(f"Comando {args} não encontrado.")
                continue

            else:
                print("Comando inválido.")
                continue

            self.client_socket.sendall(msg.encode())
            response = self.client_socket.recv(4096)
            print(response.decode())

        self.client_socket.close()

    def copy(self, args):
        """Lida com o comando de cópia de arquivos para o servidor"""
        if len(args) < 2:
            print("Uso correto: cp <origem1> <origem2> ... <destino>")
            return

        *files, destination = args
        for file_path in files:
            if not os.path.exists(file_path):
                print(f"Arquivo não encontrado: {file_path}")
                continue

            filename = os.path.basename(file_path)
            msg = f"copy {filename} {destination}"
            self.client_socket.sendall(msg.encode())

            ack = self.client_socket.recv(1024).decode()
            if ack != "ok":
                print(ack)
                continue

            # Envia o conteúdo do arquivo
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.client_socket.sendall(chunk)
            self.client_socket.sendall(b"<EOF>")

            ack = self.client_socket.recv(1024).decode()
            if ack != "done":
                print("Erro ao sincronizar com o servidor.")
                continue

            print(f"Arquivo {filename} copiado com sucesso.")

    def get(self, args):
        """Lida com o comando de download de arquivos do servidor"""
        if len(args) != 1:
            print("Uso correto: get <nome_arquivo>")
            return

        filename = args[0]
        self.client_socket.sendall(f"get {filename}".encode())

        # Aguarda resposta do servidor
        response = self.client_socket.recv(1024).decode()

        if "Pronto para enviar" not in response:
            print("Erro ao tentar baixar o arquivo.")
            return

        basename = os.path.basename(filename)
        destino = f"baixado_{basename}"
        if os.path.exists(destino):
            print(f"O arquivo '{destino}' já existe. Cancelando o download.")
            self.client_socket.sendall("cancelar".encode())
            return

        # Envia confirmação para o servidor começar
        self.client_socket.sendall("ok".encode())

        # Recebe o conteúdo do arquivo
        with open(destino, "wb") as f:
            while True:
                chunk = self.client_socket.recv(4096)
                if b"<EOF>" in chunk:
                    f.write(chunk.replace(b"<EOF>", b""))
                    break
                f.write(chunk)

        print(f"Arquivo '{filename}' salvo como '{destino}'")

    def help(self):
        print("\033[H\033[J", end="")
        print("Comandos disponíveis:")
        print("  listar | ls                  → Lista os arquivos disponíveis")
        print("  remover | rm <arquivo>       → Remove um arquivo do servidor")
        print("  copy | cp <origem> <destino> → Copia um arquivo local para o servidor")
        print("  get | baixar <arquivo>       → Baixa um arquivo do servidor")
        print("  help                         → Mostra esta mensagem de ajuda")
        print("  exit                         → Encerra a conexão\n")
        print("  clear                        → Limpa a tela do terminal")


if __name__ == "__main__":
    client = Client()
    client.connect()
