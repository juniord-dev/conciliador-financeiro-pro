import streamlit as st
import pandas as pd
import numpy as np
import io
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import warnings

# Limpeza de avisos
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Conciliador PRO | HITS x Getnet", layout="wide", page_icon="📈")

# 2. CSS CUSTOMIZADO (Design Moderno, Animações e Correção de Cores)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Reset de Cores para evitar erro no Modo Escuro */
    :root {
        --primary: #11CAA0;
        --dark-navy: #002c51;
        --light-bg: #f8fafc;
        --card-bg: #ffffff;
        --text-main: #1e293b;
    }

    .stApp { background-color: var(--light-bg); font-family: 'Inter', sans-serif; }

    /* Estilização dos Títulos e Textos */
    h1 { color: var(--dark-navy) !important; font-weight: 700 !important; }
    p { color: #64748b !important; }

    /* Caixa de Upload Customizada */
    .stFileUploader {
        border: 2px dashed var(--primary) !important;
        border-radius: 15px !important;
        background-color: var(--card-bg) !important;
        padding: 20px !important;
        transition: transform 0.3s ease;
    }
    .stFileUploader:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); }

    /* Botão Principal */
    .stButton>button {
        background: linear-gradient(135deg, #11CAA0 0%, #0da582 100%) !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 15px !important;
        transition: 0.3s all !important;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(17,202,160,0.4); }

    /* Cards de Métricas */
    [data-testid="stMetricValue"] { color: var(--dark-navy) !important; font-weight: 700 !important; }
    div[data-testid="metric-container"] {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-bottom: 4px solid var(--primary);
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO ---

def garantir_numero(serie):
    if serie.dtype == 'object':
        serie = serie.astype(str).str.replace('R$', '', regex=False).str.strip()
        serie = serie.str.replace('.', '', regex=False)
        serie = serie.str.replace(',', '.', regex=False)
    return pd.to_numeric(serie, errors='coerce').fillna(0)

def ler_excel_inteligente(file, palavra_chave, aba=0):
    try:
        df_temp = pd.read_excel(file, header=None, nrows=25, sheet_name=aba)
        for indice, linha in df_temp.iterrows():
            if linha.astype(str).str.contains(palavra_chave, case=False, na=False).any():
                return pd.read_excel(file, header=indice, sheet_name=aba)
    except:
        return pd.DataFrame()
    return pd.read_excel(file, sheet_name=aba)

# --- INTERFACE ---

st.markdown("<h1 style='text-align: center;'>Conciliação Financeira HITS x Getnet</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; margin-bottom: 40px;'>Arraste seus relatórios abaixo para iniciar o cruzamento inteligente.</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏨 Relatório HITS")
    hits_file = st.file_uploader("Insira aqui o relatório exportado do sistema de hotelaria", type=["xlsx"], key="hits")

with col2:
    st.markdown("### 💳 Relatório Getnet")
    getnet_file = st.file_uploader("Insira aqui o relatório da Getnet (incluindo aba PIX)", type=["xlsx"], key="getnet")

if hits_file and getnet_file:
    if st.button("🔥 ANALISAR E CONCILIAR AGORA"):
        with st.spinner("Navegando pelos dados e aplicando filtros de negócio..."):
            
            # --- 1. PROCESSAMENTO GETNET (CARTÕES + PIX) ---
            df_g_cartoes = ler_excel_inteligente(getnet_file, 'BANDEIRA', aba=0)
            df_g_cartoes.columns = df_g_cartoes.columns.astype(str).str.strip()
            
            # Filtro Status e Modalidade Getnet
            if 'STATUS DA TRANSAÇÃO' in df_g_cartoes.columns:
                df_g_cartoes = df_g_cartoes[df_g_cartoes['STATUS DA TRANSAÇÃO'].str.contains('Aprovada', case=False, na=False)]
            
            df_g_cartoes = df_g_cartoes.rename(columns={
                'NÚMERO DE AUTORIZAÇÃO (AUT)': 'Auto', 'NÚMERO DO COMPROVANTE DE VENDAS (CV)': 'Doc_G',
                'VALOR BRUTO': 'Valor_G', 'DATA/HORA DA VENDA': 'Data_G', 'MODALIDADE': 'Mod_G', 'BANDEIRA': 'Band_G'
            })
            df_g_cartoes = df_g_cartoes[~df_g_cartoes['Mod_G'].astype(str).str.upper().str.contains('GET ECO', na=False)]
            df_g_cartoes['Modalidade_G'] = df_g_cartoes['Band_G'].astype(str) + " " + df_g_cartoes['Mod_G'].astype(str)

            # Aba PIX Getnet
            df_g_pix = ler_excel_inteligente(getnet_file, 'VALOR', aba='PIX')
            if not df_g_pix.empty:
                col_st_pix = next((c for c in df_g_pix.columns if 'STATUS' in str(c).upper()), None)
                if col_st_pix:
                    df_g_pix = df_g_pix[df_g_pix[col_st_pix].astype(str).str.contains('Paga', case=False, na=False)]
                
                col_v_pix = next((c for c in df_g_pix.columns if 'VALOR' in str(c).upper()), None)
                col_d_pix = next((c for c in df_g_pix.columns if 'DATA' in str(c).upper()), None)
                
                df_g_pix = pd.DataFrame({
                    'Valor_G': garantir_numero(df_g_pix[col_v_pix]) if col_v_pix else 0,
                    'Data_G': df_g_pix[col_d_pix] if col_d_pix else '',
                    'Modalidade_G': 'GETNET PIX', 'Auto': 'PIX_SEM_AUT', 'Doc_G': ''
                })

            # --- 2. PROCESSAMENTO HITS ---
            df_hits = ler_excel_inteligente(hits_file, 'Autorização')
            df_hits.columns = df_hits.columns.astype(str).str.strip()
            df_hits = df_hits.rename(columns={
                'Autorização': 'Auto', 'Documento': 'Doc_H', 'Valor': 'Valor_H', 
                'Data': 'Data_H', 'Pagamento': 'Pagamento', 'Tipo de Pagamento': 'Modalidade_H'
            })
            
            # Filtros HITS (Remover Dinheiro, Faturado, Get Eco)
            filtro_h = 'FATURADO|DINHEIRO|GET ECO'
            df_hits = df_hits[~df_hits['Modalidade_H'].astype(str).str.upper().str.contains(filtro_h, regex=True)]

            # --- 3. CRUZAMENTOS ---
            # Isolar PIX
            mask_pix_h = df_hits['Modalidade_H'].astype(str).str.upper().str.contains('PIX', na=False)
            df_h_pix = df_hits[mask_pix_h].copy()
            df_h_cart = df_hits[~mask_pix_h].copy()

            # Merge Cartões (Auto)
            for df in [df_h_cart, df_g_cartoes]:
                df['Auto'] = df['Auto'].astype(str).str.strip().str.upper()
                v_col = 'Valor_H' if 'Valor_H' in df.columns else 'Valor_G'
                df[v_col] = garantir_numero(df[v_col])

            df_m_cart = pd.merge(df_h_cart, df_g_cartoes[['Auto', 'Doc_G', 'Valor_G', 'Data_G', 'Modalidade_G']], on='Auto', how='outer', indicator=True)

            # Merge PIX (Match 1 para 1 por valor)
            if not df_g_pix.empty:
                df_h_pix['Valor_H'] = garantir_numero(df_h_pix['Valor_H'])
                df_g_pix['Valor_G'] = garantir_numero(df_g_pix['Valor_G'])
                df_h_pix['Match'] = df_h_pix.groupby(df_h_pix['Valor_H'].round(2)).cumcount()
                df_g_pix['Match'] = df_g_pix.groupby(df_g_pix['Valor_G'].round(2)).cumcount()
                df_m_pix = pd.merge(df_h_pix, df_g_pix, left_on=['Valor_H', 'Match'], right_on=['Valor_G', 'Match'], how='outer', indicator=True).drop(columns=['Match'])
            else:
                df_h_pix['_merge'] = 'left_only'
                df_m_pix = df_h_pix

            # --- 4. FINALIZAÇÃO ---
            df_res = pd.concat([df_m_cart, df_m_pix], ignore_index=True)
            cond = [(df_res['_merge']=='left_only'), (df_res['_merge']=='right_only'), (df_res['_merge']=='both')]
            df_res['Status'] = np.select(cond, ['Falta na Getnet', 'Falta no HITS', 'Batido - OK'], default='Divergência')
            
            df_res['Ordem'] = df_res['Status'].map({'Falta na Getnet':1, 'Falta no HITS':2, 'Batido - OK':4})
            df_res = df_res.sort_values(by=['Ordem', 'Pagamento'])
            
            cols_final = ['Status', 'Pagamento', 'Valor_H', 'Valor_G', 'Auto', 'Doc_H', 'Doc_G', 'Data_H', 'Data_G', 'Modalidade_H', 'Modalidade_G']
            df_res = df_res[[c for c in cols_final if c in df_res.columns]].reset_index(drop=True)

            # Dashboards
            st.success("✅ Conciliação Realizada com Sucesso!")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Transações", len(df_res))
            m2.metric("Conciliados (OK)", len(df_res[df_res['Status'] == 'Batido - OK']))
            m3.metric("Pendências", len(df_res[df_res['Status'] != 'Batido - OK']))

            # Tabela Visual
            st.dataframe(df_res.style.apply(lambda x: ['background-color: #ffcccc' if val != 'Batido - OK' else 'background-color: #ccffcc' for val in x], subset=['Status'], axis=0))

            # Excel Download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, index=False, sheet_name='Resultado')
                ws = writer.sheets['Resultado']
                for row in range(2, ws.max_row + 1):
                    fill = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid") if ws.cell(row=row, column=1).value == 'Batido - OK' else PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
                    for col in range(1, ws.max_column + 1): ws.cell(row=row, column=col).fill = fill
            
            st.download_button(label="📥 BAIXAR PLANILHA DE RESULTADOS", data=output.getvalue(), file_name="conciliacao_pro.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.info("💡 Dica: Exporte os relatórios de hoje e arraste-os para as caixas acima para começar.")
