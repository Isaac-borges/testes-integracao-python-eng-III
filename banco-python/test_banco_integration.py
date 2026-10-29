import sqlite3
import pytest
from datetime import datetime


from sistema_bancario import (
    BancoRepository, Agencia, Cliente, Conta, SaldoInsuficienteError
)

@pytest.fixture
def conexao():
    """Isola a dependência externa abrindo um SQLite em memória limpo a cada teste."""
    conn = sqlite3.connect(":memory:")
    repo = BancoRepository(conn)
    repo.criar_tabelas()

    repo.salvar_agencia(Agencia(101, "São Paulo", "SP"))
    repo.salvar_cliente(Cliente("12345678900", "Maria", "12345", "São Paulo", "SP", 101))
    repo.salvar_conta(Conta(1001, 101, "12345678900", saldo=500.0))

    yield conn
    conn.close()


def test_saque_com_saldo_suficiente_atualiza_banco_e_gera_historico(conexao):
    # Arrange
    repo = BancoRepository(conexao)

    # Act
    repo.realizar_transacao(1001, "SAQUE", 200.0)

    # Assert
    cursor = conexao.execute("SELECT saldo FROM contas WHERE numero = 1001")
    saldo_no_banco = cursor.fetchone()[0]
    assert saldo_no_banco == 300.0

    # Assert
    cursor = conexao.execute("SELECT tipo, valor FROM transacoes WHERE conta_numero = 1001")
    transacao = cursor.fetchone()
    assert transacao[0] == "SAQUE"
    assert transacao[1] == 200.0


def test_saque_com_saldo_insuficiente_lanca_excecao_e_nao_altera_banco(conexao):
    # Arrange
    repo = BancoRepository(conexao)

    # Act & Assert
    with pytest.raises(SaldoInsuficienteError):
        repo.realizar_transacao(1001, "SAQUE", 1000.0)

    # Assert
    cursor = conexao.execute("SELECT saldo FROM contas WHERE numero = 1001")
    saldo_no_banco = cursor.fetchone()[0]
    assert saldo_no_banco == 500.0

    # Asserts
    cursor = conexao.execute("SELECT COUNT(*) FROM transacoes WHERE conta_numero = 1001")
    total_transacoes = cursor.fetchone()[0]
    assert total_transacoes == 0
