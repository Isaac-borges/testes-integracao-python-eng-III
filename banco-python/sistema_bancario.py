import sqlite3
from datetime import datetime
import os


# ==========================================
# 1. MODELOS DE DOMÍNIO
# ==========================================

class Agencia:
    def __init__(self, numero, cidade, estado):
        self.numero = numero
        self.cidade = cidade
        self.estado = estado

class Cliente:
    def __init__(self, cpf, nome, rg, cidade, estado, agencia_numero):
        self.cpf = cpf
        self.nome = nome
        self.rg = rg
        self.cidade = cidade
        self.estado = estado
        self.agencia_numero = agencia_numero

class Conta:
    def __init__(self, numero, agencia_numero, cliente_cpf, saldo=0.0):
        self.numero = numero
        self.agencia_numero = agencia_numero
        self.cliente_cpf = cliente_cpf
        self.saldo = saldo

class Transacao:
    def __init__(self, conta_numero, tipo, valor, id_transacao=None, data=None):
        self.id_transacao = id_transacao
        self.conta_numero = conta_numero
        self.tipo = tipo
        self.valor = valor
        self.data = data or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# 2. CAMADA DE REPOSITÓRIO E SERVIÇO
# ==========================================

class SaldoInsuficienteError(Exception):
    pass

class BancoRepository:
    def __init__(self, conexao):
        self.conn = conexao
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def criar_tabelas(self):
        schema = """
        CREATE TABLE IF NOT EXISTS agencias (
            numero INTEGER PRIMARY KEY,
            cidade TEXT NOT NULL,
            estado TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clientes (
            cpf TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            rg TEXT NOT NULL,
            cidade TEXT NOT NULL,
            estado TEXT NOT NULL,
            agencia_numero INTEGER NOT NULL,
            FOREIGN KEY (agencia_numero) REFERENCES agencias (numero)
        );
        CREATE TABLE IF NOT EXISTS contas (
            numero INTEGER PRIMARY KEY,
            agencia_numero INTEGER NOT NULL,
            cliente_cpf TEXT NOT NULL,
            saldo REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (agencia_numero) REFERENCES agencias (numero),
            FOREIGN KEY (cliente_cpf) REFERENCES clientes (cpf)
        );
        CREATE TABLE IF NOT EXISTS transacoes (
            numero INTEGER PRIMARY KEY AUTOINCREMENT,
            conta_numero INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            FOREIGN KEY (conta_numero) REFERENCES contas (numero)
        );
        """
        self.conn.executescript(schema)
        self.conn.commit()

    def salvar_agencia(self, agencia):
        self.conn.execute(
            "INSERT INTO agencias (numero, cidade, estado) VALUES (?, ?, ?)",
            (agencia.numero, agencia.cidade, agencia.estado)
        )
        self.conn.commit()

    def salvar_cliente(self, cliente):
        self.conn.execute(
            "INSERT INTO clientes (cpf, nome, rg, cidade, estado, agencia_numero) VALUES (?, ?, ?, ?, ?, ?)",
            (cliente.cpf, cliente.nome, cliente.rg, cliente.cidade, cliente.estado, cliente.agencia_numero)
        )
        self.conn.commit()

    def salvar_conta(self, conta):
        self.conn.execute(
            "INSERT INTO contas (numero, agencia_numero, cliente_cpf, saldo) VALUES (?, ?, ?, ?)",
            (conta.numero, conta.agencia_numero, conta.cliente_cpf, conta.saldo)
        )
        self.conn.commit()

    def buscar_conta(self, numero_conta):
        cursor = self.conn.execute(
            "SELECT numero, agencia_numero, cliente_cpf, saldo FROM contas WHERE numero = ?",
            (numero_conta,)
        )
        row = cursor.fetchone()
        if row:
            return Conta(numero=row[0], agencia_numero=row[1], cliente_cpf=row[2], saldo=row[3])
        return None

    def realizar_transacao(self, conta_numero, tipo, valor):
        conta = self.buscar_conta(conta_numero)
        if not conta:
            raise ValueError("Conta não encontrada.")

        if tipo == "SAQUE" and conta.saldo < valor:
            raise SaldoInsuficienteError("Saldo insuficiente para a operação.")

        novo_saldo = conta.saldo + valor if tipo == "DEPOSITO" else conta.saldo - valor


        self.conn.execute(
            "UPDATE contas SET saldo = ? WHERE numero = ?",
            (novo_saldo, conta_numero)
        )
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            "INSERT INTO transacoes (conta_numero, tipo, data, valor) VALUES (?, ?, ?, ?)",
            (conta_numero, tipo, data_atual, valor)
        )
        self.conn.commit()

    def listar_transacoes(self, conta_numero):
        cursor = self.conn.execute(
            "SELECT numero, tipo, data, valor FROM transacoes WHERE conta_numero = ? ORDER BY numero DESC",
            (conta_numero,)
        )
        return cursor.fetchall()

def menu():
    conn = sqlite3.connect(":memory:")
    repo = BancoRepository(conn)
    repo.criar_tabelas()

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n=== SISTEMA BANCÁRIO ===")
        print("1. Cadastrar Agência")
        print("2. Cadastrar Cliente")
        print("3. Abrir Conta")
        print("4. Realizar Transação (Depósito/Saque)")
        print("5. Consultar Extrato/Saldo")
        print("0. Sair")

        opcao = input("Escolha uma opção: ")

        try:
            if opcao == "1":
                num = int(input("Número da Agência: "))
                cidade = input("Cidade: ")
                uf = input("Estado (sigla): ")
                repo.salvar_agencia(Agencia(num, cidade, uf))
                print("Agência cadastrada com sucesso!")

            elif opcao == "2":
                cpf = input("CPF: ")
                nome = input("Nome: ")
                rg = input("RG: ")
                cidade = input("Cidade: ")
                uf = input("Estado (sigla): ")
                ag_num = int(input("Número da Agência do Cliente: "))
                repo.salvar_cliente(Cliente(cpf, nome, rg, cidade, uf, ag_num))
                print("Cliente cadastrado com sucesso!")

            elif opcao == "3":
                num_conta = int(input("Número da Conta: "))
                ag_num = int(input("Número da Agência: "))
                cpf = input("CPF do Cliente: ")
                repo.salvar_conta(Conta(num_conta, ag_num, cpf))
                print("Conta criada com sucesso!")

            elif opcao == "4":
                num_conta = int(input("Número da Conta: "))
                tipo = input("Tipo (DEPOSITO/SAQUE): ").upper()
                valor = float(input("Valor: "))
                repo.realizar_transacao(num_conta, tipo, valor)
                print("Transação realizada com sucesso!")

            elif opcao == "5":
                num_conta = int(input("Número da Conta: "))
                conta = repo.buscar_conta(num_conta)
                if conta:
                    print(f"\nSaldo Atual da Conta {conta.numero}: R$ {conta.saldo:.2f}")
                    transacoes = repo.listar_transacoes(num_conta)
                    print("--- Histórico de Transações ---")
                    for t in transacoes:
                        print(f"ID: {t[0]} | Tipo: {t[1]} | Data: {t[2]} | Valor: R$ {t[3]:.2f}")
                else:
                    print("Conta não encontrada.")

            elif opcao == "0":
                print("Saindo...")
                break
            else:
                print("Opção inválida.")
        except Exception as e:
            print(f"Erro: {e}")

        input("Pressione ENTER...")

if __name__ == "__main__":
    menu()
