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

# 2. CSS CUSTOMIZADO (Design, Correção do Botão e Ocultação do CSV Nativo)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    :root {
        --primary: #11CAA0;
        --dark-navy: #002c51;
        --light-bg: #f8fafc;
        --card-bg: #ffffff;
    }

    .stApp { background-color: var(--light-bg); font-family: 'Inter', sans-serif; }

    h1 { color: var(--dark-navy) !important; font-weight: 700 !important; }
    p { color: #64748b !important; }

    .stFileUploader {
        border: 2px dashed var(--primary) !important;
        border-radius: 15px !important;
        background-color: var(--card-bg) !important;
        padding: 20px !important;
        transition: transform 0.3s ease;
    }

    /* Correção do Botão: Texto Branco com Contraste Real */
    .stButton>button {
        width: 100% !important;
        background: linear-gradient(135deg, #11CAA0 0%, #0da582 100%) !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 15px !important;
        transition: 0.3s all !important;
    }
    
    .stButton>button div p, .stButton>button span, .stButton>button {
        color: white !important;
        font-weight: 700 !important;
        font-size: 16px !important;
    }

    div[data-testid="metric-container"] {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-bottom: 4px solid var(--primary);
    }
    
    /* ESCONDE O MENU NATIVO DE CSV DA TABELA DO STREAMLIT */
    [data-testid="stElementToolbar"] {
        display: none !important;
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

def limpar_cv(valor):
    v = str(valor).strip().lower()
    if v in ['nan', 'none', 'nat', 'null', '']: return ''
    if v.endswith('.0'): v = v[:-2]
    try: return str(int(v))
    except: return v

def ler_excel_inteligente(file, palavra_chave, aba=0):
    try:
        df_temp = pd.read_excel(file, header=None, nrows=25, sheet_name=aba)
        for indice, linha in df_temp.iterrows():
            if linha.astype(str).str.contains(palavra_chave, case=False, na=False).any():
                return pd.read_excel(file, header=indice, sheet_name=aba)
    except: return pd.DataFrame()
    return pd.read_excel(file, sheet_name=aba)

def formata_moeda(val):
    """Aplica formatação em Reais (R$) para exibição na tela"""
    if pd.isna(val) or val == '': return ''
    try:
        # Troca ponto por vírgula e vice-versa para o padrão BR
        return f"R$ {float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return val

# --- INTERFACE ---

st.markdown("<h1 style='text-align: center;'>Conciliação Financeira HITS x Getnet</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; margin-bottom: 40px;'>Arraste seus relatórios abaixo para iniciar o cruzamento inteligente.</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏨 Relatório HITS")
    hits_file = st.file_uploader("Insira o relatório exportado do sistema de hotelaria", type=["xlsx"], key="hits")

with col2:
    st.markdown("### 💳 Relatório Getnet")
    getnet_file = st.file_uploader("Insira o relatório da Getnet (incluindo aba PIX)", type=["xlsx"], key="getnet")

if hits_file and getnet_file:
    if st.button("ANALISAR E CONCILIAR AGORA"):
        with st.spinner("Processando..."):
            
            # --- 1. GETNET ---
            df_g_cartoes = ler_excel_inteligente(getnet_file, 'BANDEIRA', aba=0)
            df_g_cartoes.columns = df_g_cartoes.columns.astype(str).str.strip()
            if 'STATUS DA TRANSAÇÃO' in df_g_cartoes.columns:
                df_g_cartoes = df_g_cartoes[df_g_cartoes['STATUS DA TRANSAÇÃO'].str.contains('Aprovada', case=False, na=False)]
            
            df_g_cartoes = df_g_cartoes.rename(columns={
                'NÚMERO DE AUTORIZAÇÃO (AUT)': 'Auto', 'NÚMERO DO COMPROVANTE DE VENDAS (CV)': 'CV_G',
                'VALOR BRUTO': 'Valor_G', 'DATA/HORA DA VENDA': 'Data_G', 'MODALIDADE': 'Mod_G', 'BANDEIRA': 'Band_G'
            })
            df_g_cartoes = df_g_cartoes[~df_g_cartoes['Mod_G'].astype(str).str.upper().str.contains('GET ECO', na=False)]
            df_g_cartoes['Modalidade_G'] = df_g_cartoes['Band_G'].astype(str) + " " + df_g_cartoes['Mod_G'].astype(str)

            df_g_pix = ler_excel_inteligente(getnet_file, 'VALOR', aba='PIX')
            if not df_g_pix.empty:
                col_st_pix = next((c for c in df_g_pix.columns if 'STATUS' in str(c).upper()), None)
                if col_st_pix: df_g_pix = df_g_pix[df_g_pix[col_st_pix].astype(str).str.contains('Paga', case=False, na=False)]
                col_v_pix = next((c for c in df_g_pix.columns if 'VALOR' in str(c).upper()), None)
                col_d_pix = next((c for c in df_g_pix.columns if 'DATA' in str(c).upper()), None)
                df_g_pix = pd.DataFrame({
                    'Valor_G': garantir_numero(df_g_pix[col_v_pix]) if col_v_pix else 0,
                    'Data_G': df_g_pix[col_d_pix] if col_d_pix else '',
                    'Modalidade_G': 'GETNET PIX', 'Auto': 'PIX_SEM_AUT', 'CV_G': ''
                })

            # --- 2. HITS ---
            df_hits = ler_excel_inteligente(hits_file, 'Autorização')
            df_hits.columns = df_hits.columns.astype(str).str.strip()
            df_hits = df_hits.rename(columns={
                'Autorização': 'Auto', 'Documento': 'CV_H', 'Valor': 'Valor_H', 
                'Data': 'Data_H', 'Pagamento': 'Pagamento', 'Tipo de Pagamento': 'Modalidade_H'
            })
            filtro_h = 'FATURADO|DINHEIRO|GET ECO|CENTRAL TRANSFERENCIA/PIX'
            df_hits = df_hits[~df_hits['Modalidade_H'].astype(str).str.upper().str.contains(filtro_h, regex=True)]

            # --- 3. CRUZAMENTOS ---
            mask_pix_h = df_hits['Modalidade_H'].astype(str).str.upper().str.contains('PIX', na=False)
            df_h_pix, df_h_cart = df_hits[mask_pix_h].copy(), df_hits[~mask_pix_h].copy()

            for df in [df_h_cart, df_g_cartoes]:
                df['Auto'] = df['Auto'].astype(str).str.strip().str.upper()
                v_col = 'Valor_H' if 'Valor_H' in df.columns else 'Valor_G'
                df[v_col] = garantir_numero(df[v_col])

            df_m_cart = pd.merge(df_h_cart, df_g_cartoes[['Auto', 'CV_G', 'Valor_G', 'Data_G', 'Modalidade_G']], on='Auto', how='outer', indicator=True)

            if not df_g_pix.empty:
                df_h_pix['Valor_H'], df_g_pix['Valor_G'] = garantir_numero(df_h_pix['Valor_H']), garantir_numero(df_g_pix['Valor_G'])
                df_h_pix['Match'] = df_h_pix.groupby(df_h_pix['Valor_H'].round(2)).cumcount()
                df_g_pix['Match'] = df_g_pix.groupby(df_g_pix['Valor_G'].round(2)).cumcount()
                df_m_pix = pd.merge(df_h_pix, df_g_pix, left_on=['Valor_H', 'Match'], right_on=['Valor_G', 'Match'], how='outer', indicator=True).drop(columns=['Match'])
            else:
                df_h_pix['_merge'] = 'left_only'
                df_m_pix = df_h_pix

            # --- 4. TRATAMENTO E STATUS ---
            df_res = pd.concat([df_m_cart, df_m_pix], ignore_index=True)
            
            df_res['CV_H'] = df_res['CV_H'].apply(limpar_cv)
            df_res['CV_G'] = df_res['CV_G'].apply(limpar_cv)
            
            df_res['Data_H'] = pd.to_datetime(df_res['Data_H'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
            df_res['Data_G'] = pd.to_datetime(df_res['Data_G'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')

            df_res['Status'] = 'Divergência'
            df_res.loc[df_res['_merge'] == 'left_only', 'Status'] = 'Falta na Getnet'
            df_res.loc[df_res['_merge'] == 'right_only', 'Status'] = 'Falta no HITS'
            
            mask_both = df_res['_merge'] == 'both'
            mask_cv_match = (df_res['CV_H'] == df_res['CV_G'])
            mask_val_match = np.isclose(df_res['Valor_H'].fillna(0), df_res['Valor_G'].fillna(0), atol=0.01)
            
            df_res.loc[mask_both & mask_cv_match & mask_val_match, 'Status'] = 'Batido - OK'
            df_res.loc[mask_both & (~mask_cv_match | ~mask_val_match), 'Status'] = 'Divergência'

            df_res['Ordem'] = df_res['Status'].map({'Falta na Getnet':1, 'Falta no HITS':2, 'Divergência':3, 'Batido - OK':4})
            df_res = df_res.sort_values(by=['Ordem', 'Pagamento']).reset_index(drop=True)
            
            cols_f = ['Status', 'Pagamento', 'Valor_H', 'Valor_G', 'Auto', 'CV_H', 'CV_G', 'Data_H', 'Data_G', 'Modalidade_H', 'Modalidade_G']
            df_res = df_res[cols_f].fillna('')
            
            for c in df_res.columns:
                df_res[c] = df_res[c].apply(lambda x: '' if str(x).strip().lower() in ['none', 'nan', 'nat', '<na>'] else x)

            # --- CORES NA TELA ---
            def cor_tela(row):
                if row['Status'] == 'Batido - OK': est = ['background-color: #e6ffed'] * len(row)
                elif row['Status'] in ['Falta na Getnet', 'Falta no HITS']: est = ['background-color: #ffeef0'] * len(row)
                else:
                    est = ['background-color: #fff8e6'] * len(row)
                    cols = list(row.index)
                    if str(row['CV_H']) != str(row['CV_G']):
                        est[cols.index('CV_H')] = est[cols.index('CV_G')] = 'background-color: #ffb067; font-weight: bold;'
                    if not np.isclose(float(row['Valor_H'] or 0), float(row['Valor_G'] or 0), atol=0.01):
                        est[cols.index('Valor_H')] = est[cols.index('Valor_G')] = 'background-color: #ffb067; font-weight: bold;'
                return est

            # --- DASHBOARD ---
            st.success("✅ Conciliação Realizada!")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total", len(df_res))
            c2.metric("Batido OK", len(df_res[df_res['Status'] == 'Batido - OK']))
            c3.metric("Faltas (Pendências)", len(df_res[df_res['Status'].str.contains('Falta')]))
            c4.metric("Divergências", len(df_res[df_res['Status'] == 'Divergência']))

            # Exibe os dados com as cores aplicadas e a máscara de moeda R$
            st.dataframe(
                df_res.style.apply(cor_tela, axis=1).format({
                    'Valor_H': formata_moeda, 
                    'Valor_G': formata_moeda
                }), 
                use_container_width=True
            )

            # --- EXPORTAÇÃO EXCEL (.XLSX) ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, index=False, sheet_name='Resultado')
                ws = writer.sheets['Resultado']
                
                f_ok, f_err, f_div, f_warn = PatternFill("solid", "E6FFED"), PatternFill("solid", "FFEEF0"), PatternFill("solid", "FFB067"), PatternFill("solid", "FFF8E6")
                idx = {n: i for i, n in enumerate(df_res.columns, 1)}

                for r in range(2, ws.max_row + 1):
                    st_v = ws.cell(r, 1).value
                    row_f = f_ok if st_v == 'Batido - OK' else (f_err if 'Falta' in str(st_v) else f_warn)
                    for c in range(1, ws.max_column + 1): ws.cell(r, c).fill = row_f
                    
                    for c_n in ['Valor_H', 'Valor_G']:
                        if ws.cell(r, idx[c_n]).value != '':
                            ws.cell(r, idx[c_n]).number_format = '"R$" #,##0.00'
                    
                    if st_v == 'Divergência':
                        if str(ws.cell(r, idx['CV_H']).value) != str(ws.cell(r, idx['CV_G']).value):
                            ws.cell(r, idx['CV_H']).fill = ws.cell(r, idx['CV_G']).fill = f_div
                        if not np.isclose(float(ws.cell(r, idx['Valor_H']).value or 0), float(ws.cell(r, idx['Valor_G']).value or 0), atol=0.01):
                            ws.cell(r, idx['Valor_H']).fill = ws.cell(r, idx['Valor_G']).fill = f_div
            
            # ESTE É O BOTÃO DE DOWNLOAD CORRETO
            st.download_button(
                label="📥 BAIXAR RESULTADO (.xlsx)", 
                data=output.getvalue(), 
                file_name="conciliacao_pro.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("💡 Dica: Arraste os arquivos acima para começar.")
