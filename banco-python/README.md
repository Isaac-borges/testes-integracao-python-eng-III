# Sistema Bancário em Python + SQLite

Mini-sistema bancário de linha de comando que demonstra, de forma didática, a separação entre **modelos de domínio**, **camada de persistência (repositório)** e **interface de terminal (menu)**, usando SQLite como banco de dados e `pytest` para os testes de integração.

O sistema permite cadastrar agências, clientes e contas, além de realizar depósitos/saques e consultar saldo e extrato. Todo o estado é persistido em um banco SQLite — por padrão em memória (`:memory:`), o que torna a execução local descartável e mantém os testes isolados.

---

## Sumário

- [Estrutura do projeto](#estrutura-do-projeto)
- [Arquitetura](#arquitetura)
- [Modelos de domínio](#modelos-de-domínio)
- [Banco de dados](#banco-de-dados)
- [Camada de repositório](#camada-de-repositório)
- [Interface de terminal (menu)](#interface-de-terminal-menu)
- [Regras de negócio](#regras-de-negócio)
- [Testes de integração](#testes-de-integração)
- [Como executar](#como-executar)
- [Limitações e possíveis melhorias](#limitações-e-possíveis-melhorias)

---

## Estrutura do projeto

```
banco-python/
├── sistema_bancario.py        # Sistema completo: modelos, repositório e menu CLI
├── test_banco_integration.py  # Testes de integração com pytest
├── README.md                  # Esta documentação
└── venv/                      # Ambiente virtual (não versionar)
```

| Arquivo | Responsabilidade |
| --- | --- |
| `sistema_bancario.py` | Define as entidades (`Agencia`, `Cliente`, `Conta`, `Transacao`), o repositório (`BancoRepository`), a exceção de negócio e o menu interativo. |
| `test_banco_integration.py` | Testa o repositório contra um banco SQLite real em memória, verificando efeitos no banco. |

---

## Arquitetura

O código segue uma separação simples em camadas, tudo em um único módulo:

```
┌─────────────────────────────────────────┐
│  Interface (menu)                       │  Entrada/saída no terminal
├─────────────────────────────────────────┤
│  Repositório (BancoRepository)          │  Regras de acesso e persistência
│  + SaldoInsuficienteError               │  Exceção de domínio
├─────────────────────────────────────────┤
│  Modelos de domínio                     │  Agencia, Cliente, Conta, Transacao
├─────────────────────────────────────────┤
│  SQLite (conexão)                       │  Persistência relacional
└─────────────────────────────────────────┘
```

- O **repositório recebe uma conexão já pronta** (`sqlite3.Connection`), o que facilita trocar `:memory:` por um arquivo ou injetar um banco de teste.
- O **menu não conhece SQL**; ele apenas instancia modelos e chama métodos do repositório.
- A exceção `SaldoInsuficienteError` é tratada na interface (mensagem `Erro: ...`).

---

## Modelos de domínio

Classes "burras" (apenas dados, sem lógica de persistência), usadas para transportar informações entre a interface e o repositório.

### `Agencia`

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| `numero` | `int` | Número identificador da agência (chave primária). |
| `cidade` | `str` | Cidade da agência. |
| `estado` | `str` | Sigla do estado (UF). |

### `Cliente`

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| `cpf` | `str` | CPF do cliente (chave primária). |
| `nome` | `str` | Nome completo. |
| `rg` | `str` | Documento de identidade. |
| `cidade` | `str` | Cidade do cliente. |
| `estado` | `str` | Sigla do estado (UF). |
| `agencia_numero` | `int` | Agência à qual o cliente está vinculado. |

### `Conta`

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| `numero` | `int` | Número da conta (chave primária). |
| `agencia_numero` | `int` | Agência da conta. |
| `cliente_cpf` | `str` | CPF do titular. |
| `saldo` | `float` | Saldo atual (padrão `0.0`). |

### `Transacao`

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| `id_transacao` | `int \| None` | Identificador da transação (gerado pelo banco). |
| `conta_numero` | `int` | Conta movimentada. |
| `tipo` | `str` | `"DEPOSITO"` ou `"SAQUE"`. |
| `valor` | `float` | Valor movimentado. |
| `data` | `str` | Data/hora no formato `"%Y-%m-%d %H:%M:%S"` (gerada automaticamente se omitida). |

> Observação: `Transacao` é usada principalmente como estrutura de dados. Na prática, o repositório grava as transações diretamente via SQL e as devolve como tuplas em `listar_transacoes`.

---

## Banco de dados

O schema é criado por `BancoRepository.criar_tabelas()` com `CREATE TABLE IF NOT EXISTS`, sendo seguro executar repetidamente.

### Diagrama de relacionamentos

```
agencias (numero) 1 ──── N clientes (cpf, agencia_numero)
agencias (numero) 1 ──── N contas (numero, agencia_numero)
clientes (cpf)    1 ──── N contas (numero, cliente_cpf)
contas (numero)   1 ──── N transacoes (numero, conta_numero)
```

### Tabelas

**`agencias`**

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `numero` | `INTEGER` | `PRIMARY KEY` |
| `cidade` | `TEXT` | `NOT NULL` |
| `estado` | `TEXT` | `NOT NULL` |

**`clientes`**

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `cpf` | `TEXT` | `PRIMARY KEY` |
| `nome` | `TEXT` | `NOT NULL` |
| `rg` | `TEXT` | `NOT NULL` |
| `cidade` | `TEXT` | `NOT NULL` |
| `estado` | `TEXT` | `NOT NULL` |
| `agencia_numero` | `INTEGER` | `NOT NULL`, `FOREIGN KEY → agencias(numero)` |

**`contas`**

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `numero` | `INTEGER` | `PRIMARY KEY` |
| `agencia_numero` | `INTEGER` | `NOT NULL`, `FOREIGN KEY → agencias(numero)` |
| `cliente_cpf` | `TEXT` | `NOT NULL`, `FOREIGN KEY → clientes(cpf)` |
| `saldo` | `REAL` | `NOT NULL`, `DEFAULT 0.0` |

**`transacoes`**

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `numero` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` |
| `conta_numero` | `INTEGER` | `NOT NULL`, `FOREIGN KEY → contas(numero)` |
| `tipo` | `TEXT` | `NOT NULL` |
| `data` | `TEXT` | `NOT NULL` |
| `valor` | `REAL` | `NOT NULL` |

> As chaves estrangeiras estão declaradas no schema e são **efetivamente aplicadas**: o SQLite tem a verificação desligada por padrão (`PRAGMA foreign_keys = OFF`) e o PRAGMA vale **por conexão**, então `BancoRepository.__init__` executa `PRAGMA foreign_keys = ON;` sempre que recebe uma conexão. Como consequência, inserir uma conta com `cliente_cpf`/`agencia_numero` inexistente, ou um cliente com agência inexistente, lança `sqlite3.IntegrityError` (capturado pelo `except` do menu).

---

## Camada de repositório

### `SaldoInsuficienteError(Exception)`

Exceção de domínio lançada quando um saque é solicitado com valor superior ao saldo disponível.

### `BancoRepository`

Construtor: `BancoRepository(conexao)` — recebe e armazena a conexão SQLite em `self.conn` e, em seguida, habilita a integridade referencial com `PRAGMA foreign_keys = ON;`. Como o PRAGMA é uma configuração **por conexão** (e o padrão do SQLite é `OFF`), centralizá-lo no construtor garante que o menu e os testes — que criam suas próprias conexões — tenham as FKs ativas.

| Método | Assinatura | Descrição |
| --- | --- | --- |
| `criar_tabelas()` | `() -> None` | Executa o script de criação das quatro tabelas e faz `commit`. |
| `salvar_agencia(agencia)` | `(Agencia) -> None` | Insere uma agência. |
| `salvar_cliente(cliente)` | `(Cliente) -> None` | Insere um cliente. |
| `salvar_conta(conta)` | `(Conta) -> None` | Insere uma conta com o saldo informado. |
| `buscar_conta(numero_conta)` | `(int) -> Conta \| None` | Retorna a conta montada a partir da linha do banco, ou `None`. |
| `realizar_transacao(conta_numero, tipo, valor)` | `(int, str, float) -> None` | Aplica depósito/saque, atualiza o saldo e registra a transação. |
| `listar_transacoes(conta_numero)` | `(int) -> list[tuple]` | Retorna `(numero, tipo, data, valor)` da conta, mais recentes primeiro. |

#### Fluxo de `realizar_transacao`

1. Busca a conta; se não existir, lança `ValueError("Conta não encontrada.")`.
2. Se `tipo == "SAQUE"` e `saldo < valor`, lança `SaldoInsuficienteError` **antes de qualquer escrita** — garantindo que o banco permaneça inalterado.
3. Calcula o novo saldo: `saldo + valor` para `"DEPOSITO"`, `saldo - valor` para qualquer outro tipo (na prática, saque).
4. Executa `UPDATE contas SET saldo = ?` e `INSERT INTO transacoes (...)` com a data atual.
5. Faz `commit` único ao final.

> Ponto de atenção: qualquer `tipo` diferente de `"DEPOSITO"` é tratado como saque (comportamento da linha `conta.saldo - valor`). O menu normaliza a entrada com `.upper()`.

---

## Interface de terminal (menu)

A função `menu()` abre a conexão (`sqlite3.connect(":memory:")`), cria as tabelas e entra em um laço interativo. A tela é limpa a cada iteração (`cls` no Windows, `clear` nos demais).

### Opções disponíveis

| Opção | Ação | Entradas solicitadas |
| --- | --- | --- |
| `1` | Cadastrar agência | número, cidade, estado |
| `2` | Cadastrar cliente | CPF, nome, RG, cidade, estado, número da agência |
| `3` | Abrir conta | número da conta, número da agência, CPF do cliente |
| `4` | Realizar transação | número da conta, tipo (`DEPOSITO`/`SAQUE`), valor |
| `5` | Consultar extrato/saldo | número da conta |
| `0` | Sair | — |

O bloco de cada opção é envolvido por `try/except Exception`, exibindo `Erro: <mensagem>` quando algo falha (conta inexistente, saldo insuficiente, entrada inválida, violação de chave estrangeira etc.). Ao final de cada operação, o programa aguarda `ENTER`.

> Para persistir em arquivo em vez de memória, altere a linha indicada em `menu()`:
> ```python
> conn = sqlite3.connect("banco.db")  # em vez de ":memory:"
> ```

---

## Regras de negócio

- **Saldo inicial**: zero por padrão (`Conta.saldo = 0.0`), ou o valor informado.
- **Saque**: só é permitido se `saldo >= valor`; caso contrário, `SaldoInsuficienteError`.
- **Depósito**: sempre permitido, soma o valor ao saldo.
- **Histórico**: toda transação bem-sucedida gera um registro em `transacoes` com data/hora.
- **Atomicidade**: saldo e histórico são atualizados no mesmo `commit`; em caso de exceção de saldo, nada é escrito.
- **Chaves únicas**: repetir `numero` de agência/conta ou `cpf` de cliente viola a chave primária e resulta em erro do SQLite, exibido pelo `except` do menu.
- **Integridade referencial**: como `BancoRepository` habilita `PRAGMA foreign_keys = ON`, o SQLite recusa inserções que apontem para registros inexistentes (por exemplo, conta com `cliente_cpf` não cadastrado) e também impede a exclusão de registros que ainda sejam referenciados. Ambos os casos geram `sqlite3.IntegrityError`.

---

## Testes de integração

Arquivo: `test_banco_integration.py` — usa `pytest`.

### Estratégia

- **Fixture `conexao`**: abre um SQLite **em memória** novo a cada teste, cria as tabelas e insere dados controlados (*Arrange*): uma agência (101, São Paulo/SP), um cliente (CPF `12345678900`, Maria) e uma conta (1001, saldo `500.0`). Ao final, fecha a conexão (`yield` + `conn.close()`).
- Os testes instanciam um **novo `BancoRepository` sobre a mesma conexão** da fixture e verificam os efeitos consultando **diretamente o banco** com SQL, em vez de confiar apenas no retorno do repositório. Isso caracteriza um teste de **integração** (repositório + SQLite reais), não um teste unitário com mocks.
- Em cada teste, o comentário `# Arrange / # Act / # Assert` segue o padrão AAA.

### Teste 1 — `test_saque_com_saldo_suficiente_atualiza_banco_e_gera_historico`

**Cenário (caminho feliz):** saque de R$ 200,00 em conta com saldo de R$ 500,00.

**Ações e verificações:**

1. Chama `repo.realizar_transacao(1001, "SAQUE", 200.0)`.
2. Consulta `SELECT saldo FROM contas WHERE numero = 1001` e espera **300.0** (`500 − 200`).
3. Consulta `SELECT tipo, valor FROM transacoes WHERE conta_numero = 1001` e espera uma transação `("SAQUE", 200.0)`.

**Valida:** atualização correta do saldo e inserção do histórico no banco.

### Teste 2 — `test_saque_com_saldo_insuficiente_lanca_excecao_e_nao_altera_banco`

**Cenário (caminho de erro):** saque de R$ 1.000,00 em conta com saldo de R$ 500,00.

**Ações e verificações:**

1. Executa o saque dentro de `pytest.raises(SaldoInsuficienteError)`.
2. Consulta o saldo e espera que permaneça **500.0** (inalterado).
3. Consulta `SELECT COUNT(*) FROM transacoes WHERE conta_numero = 1001` e espera **0** (nenhum registro).

**Valida:** a exceção de domínio é lançada e o banco **não sofre efeitos colaterais** — confirmando que a validação ocorre antes de qualquer escrita.

### Resultado da execução

```
$ ./venv/bin/python -m pytest test_banco_integration.py -v

============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.2.0, pluggy-1.7.0
collected 2 items

test_banco_integration.py::test_saque_com_saldo_suficiente_atualiza_banco_e_gera_historico PASSED [ 50%]
test_banco_integration.py::test_saque_com_saldo_insuficiente_lanca_excecao_e_nao_altera_banco PASSED [100%]

============================== 2 passed in 0.04s ===============================
```

| Teste | Tipo de caminho | Status |
| --- | --- | --- |
| Saque com saldo suficiente | Feliz | ✅ PASSED |
| Saque com saldo insuficiente | Exceção / erro | ✅ PASSED |

### Verificação da integridade referencial

Com o `PRAGMA` habilitado no construtor do repositório, a verificação pode ser confirmada manualmente:

```python
>>> conn.execute("PRAGMA foreign_keys;").fetchone()
(1,)
>>> repo.salvar_conta(Conta(1, 999, "cpf_inexistente"))   # agência/cliente inexistentes
sqlite3.IntegrityError: FOREIGN KEY constraint failed
>>> repo.salvar_cliente(Cliente("111", "Teste", "222", "Cidade", "UF", 999))
sqlite3.IntegrityError: FOREIGN KEY constraint failed
```

### Cobertura atual

Os testes cobrem apenas **saque**. Não há testes automatizados para depósito, consulta de conta inexistente (`ValueError`), `listar_transacoes`, cadastros de agência/cliente/conta nem para violações de chave estrangeira — este último caso foi verificado apenas manualmente (veja a seção acima).

---

## Como executar

### Pré-requisitos

- Python 3.13 (compatível com versões 3.8+ em geral)
- `pytest` (apenas para os testes)

### Ambiente virtual (recomendado)

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows
pip install pytest
```

### Rodar o sistema

```bash
python3 sistema_bancario.py
```

O menu interativo será exibido. Use as opções `1` a `5` para operar e `0` para sair.

> Lembre-se: com `:memory:`, **todos os dados são perdidos ao sair**. Para persistência real, troque a conexão em `menu()` por `"banco.db"`.

### Rodar os testes

```bash
./venv/bin/python -m pytest test_banco_integration.py -v
```

ou, com o ambiente ativado:

```bash
pytest -v
```

---

## Limitações e possíveis melhorias

- **Persistência volátil por padrão**: `:memory:` descarta os dados ao encerrar.
- **Sem regras de cascata**: as FKs são validadas (`PRAGMA foreign_keys = ON`), mas não há `ON DELETE CASCADE`; excluir uma agência/cliente ainda referenciado falha com `IntegrityError`, exigindo remoção manual na ordem correta.
- **Tipos de transação sem validação explícita**: qualquer string diferente de `"DEPOSITO"` é tratada como saque; convém validar e lançar erro para tipos inválidos.
- **Sem controle de concorrência/locking**: adequado apenas para uso didático e single-user.
- **Validação de entrada no menu**: `int()`/`float()` podem lançar `ValueError`, capturado genericamente pelo `except`.
- **Cobertura de testes parcial**: adicionar casos para depósito, conta inexistente, extrato, cadastros e integridade referencial.
- **Arquivo único**: poderia ser dividido em `models.py`, `repository.py` e `cli.py` à medida que crescer.
- **`Transacao` pouco utilizada**: `realizar_transacao` e `listar_transacoes` trabalham com SQL/tuplas, não com a dataclass.
