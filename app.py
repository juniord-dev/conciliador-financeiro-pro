import streamlit as st
import pandas as pd
import numpy as np
import io
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# Configuração da página para ocupar a tela toda com um título limpo
st.set_page_config(page_title="Conciliador PRO", layout="wide", initial_sidebar_state="collapsed")

# --- INJEÇÃO DE CSS (UI/UX PREMIUM) ---
st.markdown("""
    <style>
    /* Importa a fonte Inter para um visual moderno e limpo */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Fundo geral da aplicação */
    .stApp {
        background-color: #f4f7f6;
    }
    
    /* Efeito de Glassmorphism nos painéis de upload */
    .stFileUploader {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    /* Botão Principal com visualização high-performance */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #11CAA0 0%, #0da582 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(17, 202, 160, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(17, 202, 160, 0.6);
        background: linear-gradient(135deg, #0da582 0%, #0b8c6e 100%);
    }

    /* Cards de métricas do Streamlit */
    div[data-testid="metric-container"] {
        background-color: white;
        border-radius: 12px;
        padding: 15px 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #11CAA0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CABEÇALHO DA INTERFACE ---
st.markdown("<h1 style='text-align: center; color: #1e293b; margin-bottom: 0;'>Conciliação Financeira</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 18px; margin-bottom: 40px;'>Automatize o cruzamento do seu sistema de gestão com as adquirentes.</p>", unsafe_allow_html=True)


def garantir_numero(serie):
    if serie.dtype == 'object':
        serie = serie.astype(str).str.replace('R$', '', regex=False).str.strip()
        serie = serie.str.replace('.', '', regex=False)
        serie = serie.str.replace(',', '.', regex=False)
    return pd.to_numeric(serie, errors='coerce').fillna(0)

def ler_excel_dinamico(file, palavra_chave, aba=0):
    try:
        df_temp = pd.read_excel(file, header=None, nrows=20, sheet_name=aba)
        for indice, linha in df_temp.iterrows():
            if linha.astype(str).str.contains(palavra_chave, case=False, na=False).any():
                return pd.read_excel(file, header=indice, sheet_name=aba)
    except:
        return pd.DataFrame()
    return pd.read_excel(file, sheet_name=aba)

# Interface de Upload
col1, col2 = st.columns(2)
with col1:
    hits_file = st.file_uploader("📂 Upload Planilha HITS", type=["xlsx"])
with col2:
    getnet_file = st.file_uploader("📂 Upload Planilha Getnet", type=["xlsx"])

if hits_file and getnet_file:
    if st.button("Executar Conciliação"):
        with st.spinner("Processando dados..."):
            
            # --- CARGA GETNET ---
            df_g_cartoes = ler_excel_dinamico(getnet_file, 'BANDEIRA', aba=0)
            if 'STATUS DA TRANSAÇÃO' in df_g_cartoes.columns:
                df_g_cartoes = df_g_cartoes[df_g_cartoes['STATUS DA TRANSAÇÃO'].str.contains('Aprovada', case=False, na=False)]
            
            df_g_cartoes = df_g_cartoes.rename(columns={
                'NÚMERO DE AUTORIZAÇÃO (AUT)': 'Auto',
                'NÚMERO DO COMPROVANTE DE VENDAS (CV)': 'Doc_G',
                'VALOR BRUTO': 'Valor_G',
                'DATA/HORA DA VENDA': 'Data_G',
                'MODALIDADE': 'Modalidade_G',
                'BANDEIRA': 'Bandeira_G'
            })
            df_g_cartoes = df_g_cartoes[~df_g_cartoes['Modalidade_G'].astype(str).str.upper().str.contains('GET ECO', na=False)]

            # --- CARGA PIX GETNET ---
            df_g_pix = ler_excel_dinamico(getnet_file, 'VALOR', aba='PIX')
            if not df_g_pix.empty:
                col_status = next((c for c in df_g_pix.columns if 'STATUS' in str(c).upper()), None)
                if col_status:
                    df_g_pix = df_g_pix[df_g_pix[col_status].astype(str).str.contains('Paga', case=False, na=False)]
                
                col_v = next((c for c in df_g_pix.columns if 'VALOR' in str(c).upper()), None)
                col_d = next((c for c in df_g_pix.columns if 'DATA' in str(c).upper()), None)
                
                df_g_pix = pd.DataFrame({
                    'Valor_G': garantir_numero(df_g_pix[col_v]) if col_v else 0,
                    'Data_G': df_g_pix[col_d] if col_d else '',
                    'Modalidade_G': 'GETNET PIX',
                    'Auto': 'PIX_SEM_AUT',
                    'Doc_G': ''
                })

            # --- CARGA HITS ---
            df_hits = ler_excel_dinamico(hits_file, 'Autorização')
            df_hits = df_hits.rename(columns={
                'Autorização': 'Auto', 'Documento': 'Doc_H', 'Valor': 'Valor_H', 
                'Data': 'Data_H', 'Pagamento': 'Pagamento', 'Tipo de Pagamento': 'Modalidade_H'
            })
            remover = 'FATURADO|DINHEIRO|GET ECO'
            df_hits = df_hits[~df_hits['Modalidade_H'].astype(str).str.upper().str.contains(remover, regex=True)]

            # --- SEPARAÇÃO CARTÃO/PIX ---
            mask_pix = df_hits['Modalidade_H'].astype(str).str.upper().str.contains('PIX', na=False)
            df_h_pix = df_hits[mask_pix].copy()
            df_h_cartoes = df_hits[~mask_pix].copy()

            # Normalização Auto e Valores
            for df in [df_h_cartoes, df_g_cartoes]:
                df['Auto'] = df['Auto'].astype(str).str.strip().str.upper()
                df['Valor_H' if 'Valor_H' in df.columns else 'Valor_G'] = garantir_numero(df['Valor_H' if 'Valor_H' in df.columns else 'Valor_G'])

            # --- MERGE CARTÕES ---
            df_m_cartoes = pd.merge(df_h_cartoes, df_g_cartoes[['Auto', 'Doc_G', 'Valor_G', 'Data_G', 'Modalidade_G']], on='Auto', how='outer', indicator=True)

            # --- MERGE PIX ---
            if not df_g_pix.empty:
                df_h_pix['Valor_H'] = garantir_numero(df_h_pix['Valor_H'])
                df_h_pix['Match'] = df_h_pix.groupby(df_h_pix['Valor_H'].round(2)).cumcount()
                df_g_pix['Match'] = df_g_pix.groupby(df_g_pix['Valor_G'].round(2)).cumcount()
                df_m_pix = pd.merge(df_h_pix, df_g_pix, left_on=['Valor_H', 'Match'], right_on=['Valor_G', 'Match'], how='outer', indicator=True).drop(columns=['Match'])
            else:
                df_h_pix['_merge'] = 'left_only'
                df_m_pix = df_h_pix

            # Resultado Final
            df_res = pd.concat([df_m_cartoes, df_m_pix], ignore_index=True)
            cond = [(df_res['_merge']=='left_only'), (df_res['_merge']=='right_only'), (df_res['_merge']=='both')]
            df_res['Status'] = np.select(cond, ['Falta na Getnet', 'Falta no HITS', 'Batido - OK'], default='Divergência')
            
            # --- CORREÇÃO AQUI: ORDENAÇÃO ANTES DE CORTAR AS COLUNAS ---
            df_res['Ordem'] = df_res['Status'].map({'Falta na Getnet':1, 'Falta no HITS':2, 'Divergência':3, 'Batido - OK':4})
            df_res = df_res.sort_values(by=['Ordem', 'Pagamento']) # Ordena primeiro!
            
            cols_desejadas = ['Status', 'Pagamento', 'Valor_H', 'Valor_G', 'Auto', 'Doc_H', 'Doc_G', 'Data_H', 'Data_G', 'Modalidade_H', 'Modalidade_G']
            cols_existentes = [c for c in cols_desejadas if c in df_res.columns] # Pega só o que existe para evitar erro
            
            df_res = df_res[cols_existentes].reset_index(drop=True) # Agora sim corta as colunas

            # --- EXPORTAÇÃO COM FORMATAÇÃO ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, index=False, sheet_name='Resultado')
                ws = writer.sheets['Resultado']
                
                # Cores
                red_fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
                green_fill = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid")
                
                for row in range(2, ws.max_row + 1):
                    status_val = ws.cell(row=row, column=1).value
                    fill = green_fill if status_val == 'Batido - OK' else red_fill
                    for col in range(1, ws.max_column + 1):
                        ws.cell(row=row, column=col).fill = fill
                          
# --- DASHBOARD DE RESULTADOS (Métricas Visuais) ---
            st.success("✅ Conciliação finalizada com sucesso!")
            
            # Conta os status
            total_transacoes = len(df_res)
            batidos = len(df_res[df_res['Status'] == 'Batido - OK'])
            divergencias = total_transacoes - batidos
            
            # Cria 3 colunas para os cards
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric("Total de Transações", total_transacoes)
            metric_col2.metric("Conciliados (OK)", batidos)
            metric_col3.metric("Divergências Encontradas", divergencias, delta=f"-{divergencias} pendências" if divergencias > 0 else "Tudo Certo!", delta_color="inverse")
            
            st.markdown("<br>", unsafe_allow_html=True)
            # --------------------------------------------------
            st.dataframe(df_res.style.apply(lambda x: ['background-color: #ffcccc' if val != 'Batido - OK' else 'background-color: #ccffcc' for val in x], subset=['Status'], axis=0))
            
            st.download_button(
                label="📥 Baixar Resultado Formatado",
                data=output.getvalue(),
                file_name="resultado_conciliacao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("Aguardando o upload das duas planilhas para iniciar...")