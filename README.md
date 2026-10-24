# Conversor de EPUB para PDF de Impressão Econômica (`impr`)

Este projeto consiste em um script Python que automatiza a conversão de livros digitais no formato **EPUB** para arquivos **PDF** prontos e otimizados para impressão econômica frente e verso em folhas A4 (tamanho A5 impresso lado a lado com imposição e linha de corte central tracejada).

---

## 🚀 Funcionalidades

- **Layout A5 em Folha A4**: Posiciona automaticamente duas páginas A5 por face de folha A4 em formato Paisagem.
- **Vários Modos de Imposição**:
  - **Corte e Empilhamento (`cut-stack`)** *(Recomendado)*: Ideal para cortar as folhas impressas ao meio com guilhotina ou estilete e empilhar a metade esquerda sobre a direita, mantendo a leitura contínua.
  - **Livreto (`booklet`)**: Prepara as páginas em cadernos (assinaturas) de tamanho customizável (ex: 16 páginas) para dobrar as folhas A4 ao meio e costurar ou grampear.
  - **Sequencial (`sequencial`)**: Posiciona as páginas lado a lado em ordem de leitura normal.
- **Filtro de Capítulos**: Permite selecionar capítulos específicos para imprimir (ex: `'1-3'`, `'2,5'`) ou processar o livro completo.
- **Customização Visual**: Ajuste de tamanho de fonte, margem e família da fonte (serif/sans-serif).
- **Numeração Automática**: Insere rodapés de numeração de páginas centralizados de forma independente e limpa.
- **Linha de Corte**: Desenha uma linha central cinza tracejada para auxiliar no corte exato das páginas.

---

## 📦 Requisitos

1. **Python 3** instalado.
2. Dependências de execução instaladas em um ambiente virtual recomendado:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```
3. Um navegador baseado no Chromium instalado para renderizar os capítulos HTML em PDF no modo *headless*.

   O script procura automaticamente Brave, Google Chrome, Chromium e Microsoft Edge, tanto em instalações nativas quanto via Flatpak.

---

## 📂 Estrutura do Projeto

```text
impr/
├── epub/                 # Pasta dedicada para colocar seus livros .epub de entrada
├── pdf/                  # Pasta onde os PDFs finais gerados são salvos automaticamente
├── .gitignore            # Ignora temporários (__pycache__) e arquivos epub/pdf do Git
├── README.md             # Esta documentação do projeto
├── requirements.txt      # Dependência de execução
├── requirements-dev.txt  # Dependências para testes
├── pytest.ini            # Configuração do pytest
├── tests/                # Testes automatizados
└── epub_to_print_pdf.py  # Script Python principal
```

---

## 🛠️ Como Usar

O script suporta tanto um **modo interativo amigável** (com perguntas no terminal) quanto um **modo CLI de linha de comando** rápido.

### 1. Modo Interativo

Coloque o livro `.epub` na pasta `epub/` e simplesmente execute o script sem parâmetros:

```bash
.venv/bin/python epub_to_print_pdf.py
```

O script guiará você nas seguintes escolhas:
1. Selecionar qual livro deseja processar (dentre os listados na pasta `epub/`).
2. Digitar o intervalo de capítulos (ou deixar em branco para o livro completo).
3. Selecionar o modo de imposição (`cut-stack`, `sequencial` ou `booklet`).
4. Customizar tamanho de fonte e margem da página.
5. Caminho do arquivo de saída (com geração de nome automática inteligente e reduzida).

---

### 2. Modo de Linha de Comando (CLI)

Passe o caminho do EPUB e os argumentos diretamente para rodar sem interações:

```bash
# Exemplo 1: Processar apenas o capítulo 1 no modo cut-stack (corte e empilhamento)
.venv/bin/python epub_to_print_pdf.py epub/livro.epub -c 1 --mode cut-stack

# Exemplo 2: Processar capítulos 1 a 5 no modo livreto (booklet) com caderno de 16 páginas
.venv/bin/python epub_to_print_pdf.py epub/livro.epub -c 1-5 --mode booklet --signature-size 16

# Exemplo 3: Customizar margens e fonte para o livro inteiro
.venv/bin/python epub_to_print_pdf.py epub/livro.epub -m "20mm" -f "14pt" --font-family "sans-serif"
```

#### Parâmetros Disponíveis:
- `epub`: Caminho do arquivo EPUB de entrada.
- `-o`, `--output`: Caminho do PDF de saída (gerado de forma inteligente caso omitido).
- `-f`, `--font-size`: Tamanho da fonte CSS (padrão: `12.5pt`).
- `-m`, `--margin`: Margem da página (padrão: `15mm`).
- `--font-family`: Família da fonte a ser injetada (padrão: `serif`).
- `--mode`: Modo de imposição (`cut-stack`, `sequencial`, `booklet`).
- `-s`, `--signature-size`: Tamanho da assinatura para livreto (deve ser múltiplo de 4, padrão: `16`).
- `-c`, `--chapters`: Filtro de capítulos (ex: `'1-3'`, `'2,4'`, `'5'`).
- `--browser`: Caminho ou nome customizado do executável Chromium.

---

## ⚡ Atalho no Zsh

Para rodar o utilitário a partir de **qualquer diretório** usando o comando `impr`, adicione a função abaixo ao `~/.zshrc`:

1. Abra o arquivo de configuração do Zsh com o comando:
   ```bash
   nvim ~/.zshrc
   ```
2. Cole a função abaixo no final do arquivo:
   ```zsh
   impr() {
       /home/henrique/projetos/impr/.venv/bin/python \
           /home/henrique/projetos/impr/epub_to_print_pdf.py "$@"
   }
   ```
3. Salve, feche o editor e recarregue o perfil na aba atual do terminal:
   ```bash
   source ~/.zshrc
   ```

A partir de agora, basta digitar `impr` de qualquer diretório. O modo interativo usará as pastas `epub/` e `pdf/` deste projeto, enquanto caminhos informados explicitamente continuarão sendo aceitos.

## 🧪 Testes

Para instalar as dependências de desenvolvimento e executar a suíte:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Os testes unitários não exigem Brave, Chrome, Chromium ou Edge instalado.
