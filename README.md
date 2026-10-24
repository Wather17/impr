# Conversor de EPUB para PDF de Impressão Econômica (`impr`)

Este projeto converte livros digitais no formato **EPUB** em arquivos **PDF** otimizados para impressão econômica frente e verso em folhas A4. O resultado usa páginas A5 lado a lado, imposição configurável e linha de corte central tracejada.

## 🚀 Funcionalidades

- **Layout A5 em folha A4**: posiciona duas páginas A5 por face de uma folha A4 em formato paisagem.
- **Modos de imposição**:
  - **Corte e Empilhamento (`cut-stack`)** *(recomendado)*: para cortar as folhas ao meio e empilhar as metades.
  - **Livreto (`booklet`)**: prepara cadernos de tamanho configurável para dobrar e grampear ou costurar.
  - **Sequencial (`sequencial`)**: posiciona as páginas lado a lado em ordem de leitura normal.
- **Filtro de capítulos**: seleciona capítulos como `1-3` ou `2,5`, ou processa o livro completo.
- **Customização visual**: ajusta tamanho da fonte, margem e família tipográfica.
- **Numeração automática**: insere números de página no rodapé.
- **Linha de corte**: desenha uma linha central tracejada para auxiliar o corte.

## 📦 Requisitos do sistema

- Linux com Bash.
- Python **3.9 ou superior**.
- Suporte ao módulo `venv` instalado para a versão do Python usada.
- Um navegador baseado em Chromium para renderizar HTML em PDF no modo *headless*.

O projeto procura automaticamente por Brave, Google Chrome, Chromium e Microsoft Edge, tanto em instalações nativas quanto via Flatpak. O navegador é uma dependência externa: o projeto detecta e orienta, mas não instala pacotes do sistema ou navegadores automaticamente.

Se o módulo `venv` não estiver disponível, instale o pacote correspondente na sua distribuição — normalmente chamado `python3-venv` — e repita a instalação. Essa etapa é responsabilidade do sistema e não usa `sudo` automaticamente.

## 📥 Instalação recomendada

A instalação é feita por usuário, mantém a `.venv` dentro do checkout e não altera arquivos de configuração do Bash ou Zsh.

A partir da raiz do checkout:

```bash
bash scripts/install-linux.sh
```

O instalador:

- cria ou reutiliza `.venv`;
- instala as dependências de execução;
- cria `epub/` e `pdf/`;
- instala o launcher `impr` em `~/.local/bin/`;
- informa se `~/.local/bin` ainda não estiver no `PATH`.

Se o diretório não estiver no `PATH` da sessão atual, use o comando exibido pelo instalador. Para tornar a configuração permanente, adicione manualmente `export PATH="$HOME/.local/bin:$PATH"` ao perfil do seu shell.

Depois da instalação, valide o ambiente antes da primeira conversão:

```bash
impr --check
```

O diagnóstico verifica Python, `pypdf`, navegador Chromium e permissões de leitura e escrita em `epub/` e `pdf/`. Ele termina com código zero quando o ambiente está pronto e com código não-zero quando alguma dependência precisa ser corrigida.

### Opções de instalação

```bash
# Instala também as dependências de desenvolvimento
bash scripts/install-linux.sh --dev

# Atualiza/reconcilia a instalação existente
bash scripts/install-linux.sh --update

# Remove somente o launcher gerenciado; preserva código, .venv, epub/ e pdf/
bash scripts/install-linux.sh --uninstall
```

O instalador não sobrescreve um arquivo `~/.local/bin/impr` que não tenha sido criado por ele.

### Navegador personalizado

Se o navegador não estiver em um dos nomes detectados automaticamente, informe o executável explicitamente:

```bash
impr --check --browser /caminho/para/chromium
impr epub/livro.epub --browser /caminho/para/chromium
```

## 📂 Estrutura do Projeto

```text
impr/
├── epub/                 # EPUBs de entrada
├── pdf/                  # PDFs finais gerados automaticamente
├── .venv/                # Ambiente virtual local, ignorado pelo Git
├── scripts/
│   └── install-linux.sh  # Instalador user-scoped
├── tests/                # Testes automatizados
├── README.md             # Esta documentação
├── requirements.txt      # Dependências de execução
├── requirements-dev.txt  # Dependências de desenvolvimento
├── pytest.ini            # Configuração do pytest
└── epub_to_print_pdf.py  # Script Python principal
```

Os diretórios automáticos `epub/` e `pdf/` pertencem ao checkout do projeto, não ao diretório atual do terminal. Por isso, executar `impr` de qualquer lugar continua usando os dados do projeto instalado.

## 🛠️ Como usar

O launcher suporta modo interativo e modo CLI. Coloque um EPUB em `epub/` para usar a seleção automática ou informe um caminho explícito.

### 1. Modo interativo

```bash
impr
```

O script permite:

1. selecionar o EPUB;
2. escolher capítulos ou deixar em branco para o livro completo;
3. selecionar `cut-stack`, `sequencial` ou `booklet`;
4. customizar fonte e margem;
5. escolher o caminho do PDF de saída.

### 2. Modo CLI

```bash
# Processar apenas o capítulo 1 no modo cut-stack
impr epub/livro.epub -c 1 --mode cut-stack

# Processar capítulos 1 a 5 no modo livreto
impr epub/livro.epub -c 1-5 --mode booklet --signature-size 16

# Customizar margem e fonte para o livro inteiro
impr epub/livro.epub -m "20mm" -f "14pt" --font-family "sans-serif"
```

Filtros válidos selecionam exatamente os capítulos indicados. Um intervalo invertido, como `5-2`, é normalizado para `2-5`. Filtros fora do intervalo ou com componentes inválidos interrompem a execução sem gerar PDF.

#### Parâmetros disponíveis

- `epub`: caminho do arquivo EPUB de entrada.
- `-o`, `--output`: caminho do PDF de saída; se omitido, o nome é gerado automaticamente.
- `-f`, `--font-size`: tamanho da fonte CSS (padrão: `12.5pt`).
- `-m`, `--margin`: margem da página PDF A5 (padrão: `15mm`).
- `--font-family`: família da fonte (padrão: `serif`).
- `--mode`: modo de imposição (`cut-stack`, `sequencial` ou `booklet`).
- `-s`, `--signature-size`: tamanho da assinatura para `booklet`, múltiplo de 4 (padrão: `16`).
- `-c`, `--chapters`: filtro de capítulos, como `1-3`, `2,4` ou `5`.
- `--browser`: caminho ou nome customizado do executável Chromium.
- `--check`: diagnostica o ambiente sem exigir EPUB ou gerar PDF.

### Execução direta para desenvolvimento

O launcher é o caminho recomendado para uso normal. Para desenvolver ou depurar o script, a execução direta continua disponível:

```bash
.venv/bin/python epub_to_print_pdf.py epub/livro.epub -c 1
```

## 🧪 Testes

Instale as dependências de desenvolvimento e execute a suíte:

```bash
bash scripts/install-linux.sh --dev
.venv/bin/python -m pytest -q
```

Validações auxiliares do instalador:

```bash
bash -n scripts/install-linux.sh
bash scripts/install-linux.sh --help
```

Os testes unitários não exigem Brave, Chrome, Chromium ou Edge instalado; a conversão real exige um navegador compatível.
