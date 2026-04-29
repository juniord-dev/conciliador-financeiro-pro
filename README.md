# 📈 Conciliador Financeiro PRO: HITS x Getnet

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)

Uma solução de alta performance desenvolvida para automatizar a conciliação bancária entre o sistema de hotelaria **HITS** e a adquirente **Getnet**. Este Web App elimina o trabalho manual, reduz erros operacionais e identifica divergências financeiras em segundos.

---

## ✨ Funcionalidades Principais

* **Cruzamento Inteligente de Cartões:** Identificação automática via código de Autorização (Auto), com tratamento para diferenças de caixa (maiúsculas/minúsculas).
* **Motor de Conciliação PIX:** Algoritmo exclusivo de "Match 1 para 1" para transações PIX (aba separada da Getnet), cruzando dados por valor exato mesmo sem códigos de autorização.
* **Filtros de Regras de Negócio:** * Exclusão automática de modalidades irrelevantes (Ex: GET ECO, DINHEIRO, FATURADO).
    * Processamento estrito de transações com status "Aprovada" ou "Paga".
* **Interface Premium (UI/UX):** Design moderno com tipografia Inter, cards de métricas em tempo real e suporte a temas.
* **Relatório Formatado:** Exportação para Excel com formatação condicional (Verde para OK, Vermelho para pendências) e filtros ativos.

---

## 🛠️ Tecnologias Utilizadas

* **Python:** Linguagem base para processamento de dados.
* **Streamlit:** Framework para criação da interface web interativa.
* **Pandas:** Biblioteca robusta para manipulação e cruzamento de grandes volumes de dados.
* **Openpyxl:** Motor para geração e estilização de arquivos Excel (.xlsx).

---

## 🚀 Como Utilizar

### Na Nuvem (Recomendado)
Acesse o sistema diretamente pelo navegador através do link:
👉 `[Acessar o Conciliador Financeiro](https://conciliador-financeiro-pro.streamlit.app/)`

### Localmente (Desenvolvimento)
Se desejar rodar o projeto em sua máquina:

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/juniord-dev/conciliador-financeiro-pro.git
    cd seu-repositorio
    ```

2.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Inicie a aplicação:**
    ```bash
    streamlit run app.py
    ```

---

## 📁 Estrutura do Projeto

* `app.py`: Código principal contendo a interface e a lógica de conciliação.
* `requirements.txt`: Lista de bibliotecas necessárias para o funcionamento do sistema.
* `README.md`: Documentação do projeto.

---

## 👨‍💻 Desenvolvedor

Desenvolvido por **Junior Dantas** — Especialista em Soluções Digitais e Automação.

---
*Nota: Este projeto foi desenvolvido com foco em performance e facilidade de uso para departamentos financeiros e hoteleiros.*
