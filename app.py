import streamlit as st
import pandas as pd
import numpy as np
import io
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import warnings

# Limpeza de avisos
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 1. CONFIGURAÇÃO DA PÁGINA E CSS
st.set_page_config(page_title="Conciliador PRO | HITS x Getnet", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    :root { --primary: #11CAA0; --dark-navy: #002c51; --light-bg: #f8fafc; --card-bg: #ffffff; }
    .stApp { background-color: var(--light-bg); font-family: 'Inter', sans-serif; }
    h1 { color: var(--dark-navy) !important; font-weight: 700 !important; }
    p { color: #64748b !important; }
    .stFileUploader {
        border: 2px dashed var(--primary) !important; border-radius: 15px !important;
        background-color: var(--card-bg) !important; padding: 20px !important; transition: transform 0.3s ease;
    }
    .stButton>button {
        width: 100% !important; background: linear-gradient(135deg, #11CAA0 0%, #0da582 100%) !important;
        border-radius: 10px !important; border: none !important; padding: 15px !important; transition: 0.3s all !important;
    }
    .stButton>button div p, .stButton>button span, .stButton>button {
        color: white !important; font-weight: 700 !important; font-size: 16px !important;
    }
    div[data-testid="metric-container"] {
        background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-bottom: 4px solid var(--primary);
    }
    [data-testid="stElementToolbar"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO ---

def garantir_numero(serie):
    if serie.dtype == 'object':
        serie = serie.astype(str).str.replace('R$', '', regex=False).str.strip()
        serie = serie.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
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
    if pd.isna(val) or val == '': return ''
    try: return f"R$ {float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return val

# --- INTERFACE ---

st.markdown("<h1 style='text-align: center;'>Conciliação Financeira HITS x Getnet</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; margin-bottom: 40px;'>Arraste seus relatórios abaixo para iniciar o cruzamento inteligente.</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1: hits_file = st.file_uploader("🏨 Relatório HITS", type=["xlsx"], key="hits")
with col2: getnet_file = st.file_uploader("💳 Relatório Getnet", type=["xlsx"], key="getnet")

if hits_file and getnet_file:
    if st.button("ANALISAR E CONCILIAR AGORA"):
        with st.spinner("Processando Inteligência Financeira..."):
            
            # --- 1. GETNET ---
            df_g_cartoes = ler_excel_inteligente(getnet_file, 'BANDEIRA', aba=0)
            df_g_cartoes.columns = df_g_cartoes.columns.astype(str).str.strip().str.upper()
            
            if 'MODALIDADE' not in df_g_cartoes.columns:
                st.error("❌ ERRO: Coluna de Modalidade ausente. Verifique se os arquivos não foram invertidos.")
                st.stop()

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
                df_g_pix.columns = df_g_pix.columns.astype(str).str.strip().str.upper()
                col_st_pix = next((c for c in df_g_pix.columns if 'STATUS' in str(c)), None)
                if col_st_pix: df_g_pix = df_g_pix[df_g_pix[col_st_pix].astype(str).str.contains('Paga', case=False, na=False)]
                col_v_pix = next((c for c in df_g_pix.columns if 'VALOR' in str(c)), None)
                col_d_pix = next((c for c in df_g_pix.columns if 'DATA' in str(c)), None)
                df_g_pix = pd.DataFrame({
                    'Valor_G': garantir_numero(df_g_pix[col_v_pix]) if col_v_pix else 0,
                    'Data_G': df_g_pix[col_d_pix] if col_d_pix else '',
                    'Modalidade_G': 'GETNET PIX', 'Auto': 'PIX_SEM_AUT', 'CV_G': ''
                })

            # --- 2. HITS ---
            df_hits = ler_excel_inteligente(hits_file, 'Autorização')
            df_hits.columns = df_hits.columns.astype(str).str.strip()
            
            # Garante que a coluna Usuário exista mesmo se mudar no sistema
            if 'Usuário' not in df_hits.columns: df_hits['Usuário'] = ''
                
            df_hits = df_hits.rename(columns={
                'Autorização': 'Auto', 'Documento': 'CV_H', 'Valor': 'Valor_H', 
                'Data': 'Data_H', 'Pagamento': 'Pagamento', 'Tipo de Pagamento': 'Modalidade_H', 'Usuário': 'Usuário'
            })
            # Não filtramos "HOTEL TRANSFERENCIA/PIX MANUAL" aqui, para podermos marcá-lo como "A VERIFICAR" depois
            filtro_h = 'FATURADO|DINHEIRO|GET ECO|CENTRAL TRANSFERENCIA/PIX'
            df_hits = df_hits[~df_hits['Modalidade_H'].astype(str).str.upper().str.contains(filtro_h, regex=True)]

            # --- 3. CRUZAMENTOS MAIN ---
            mask_pix_h = df_hits['Modalidade_H'].astype(str).str.upper().str.contains('PIX', na=False)
            df_h_pix, df_h_cart = df_hits[mask_pix_h].copy(), df_hits[~mask_pix_h].copy()

            for df in [df_h_cart, df_g_cartoes]:
                df['Auto'] = df['Auto'].astype(str).str.strip().str.upper()
                df['Valor_H' if 'Valor_H' in df.columns else 'Valor_G'] = garantir_numero(df['Valor_H' if 'Valor_H' in df.columns else 'Valor_G'])

            df_m_cart = pd.merge(df_h_cart, df_g_cartoes[['Auto', 'CV_G', 'Valor_G', 'Data_G', 'Modalidade_G']], on='Auto', how='outer', indicator=True)

            if not df_g_pix.empty:
                df_h_pix['Valor_H'], df_g_pix['Valor_G'] = garantir_numero(df_h_pix['Valor_H']), garantir_numero(df_g_pix['Valor_G'])
                df_h_pix['Match'] = df_h_pix.groupby(df_h_pix['Valor_H'].round(2)).cumcount()
                df_g_pix['Match'] = df_g_pix.groupby(df_g_pix['Valor_G'].round(2)).cumcount()
                df_m_pix = pd.merge(df_h_pix, df_g_pix, left_on=['Valor_H', 'Match'], right_on=['Valor_G', 'Match'], how='outer', indicator=True).drop(columns=['Match'])
            else:
                df_h_pix['_merge'] = 'left_only'
                df_m_pix = df_h_pix

            # --- 4. TRATAMENTO, PAREAMENTO E STATUS ---
            df_res = pd.concat([df_m_cart, df_m_pix], ignore_index=True)
            df_res['ID_Match'] = '' # Nova Coluna de ID
            
            df_res['CV_H'] = df_res['CV_H'].apply(limpar_cv)
            df_res['CV_G'] = df_res['CV_G'].apply(limpar_cv)
            
            df_res['Data_H'] = pd.to_datetime(df_res['Data_H'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
            df_res['Data_G'] = pd.to_datetime(df_res['Data_G'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')

            df_res['Status'] = 'Divergência'
            df_res.loc[df_res['_merge'] == 'left_only', 'Status'] = 'Falta na Getnet'
            df_res.loc[df_res['_merge'] == 'right_only', 'Status'] = 'Falta no HITS'
            
            mask_both = df_res['_merge'] == 'both'
            mask_cv_match = (df_res['CV_H'] == df_res['CV_G'])
            mask_val_match = np.isclose(pd.to_numeric(df_res['Valor_H'], errors='coerce').fillna(0), pd.to_numeric(df_res['Valor_G'], errors='coerce').fillna(0), atol=0.01)
            
            df_res.loc[mask_both & mask_cv_match & mask_val_match, 'Status'] = 'Batido - OK'
            df_res.loc[mask_both & (~mask_cv_match | ~mask_val_match), 'Status'] = 'Divergência'

            # INTELIGÊNCIA: PAREAMENTO "ERRO NO AUTO"
            def get_data_curta(d): return str(d)[:10] if pd.notna(d) and d != '' else ''
            
            mask_fh = df_res['Status'] == 'Falta na Getnet'
            mask_fg = df_res['Status'] == 'Falta no HITS'
            
            df_res['K_H'] = df_res['Valor_H'].astype(float).round(2).astype(str) + "_" + df_res['Data_H'].apply(get_data_curta)
            df_res['K_G'] = df_res['Valor_G'].astype(float).round(2).astype(str) + "_" + df_res['Data_G'].apply(get_data_curta)
            
            chaves_comuns = set(df_res.loc[mask_fh, 'K_H']).intersection(set(df_res.loc[mask_fg, 'K_G']))
            chaves_comuns = [c for c in chaves_comuns if not c.startswith('0.0_') and not c.startswith('nan_')]
            
            id_count = 1
            for k in chaves_comuns:
                idx_h = df_res[(mask_fh) & (df_res['K_H'] == k)].index
                idx_g = df_res[(mask_fg) & (df_res['K_G'] == k)].index
                limite = min(len(idx_h), len(idx_g))
                
                for i in range(limite):
                    df_res.loc[idx_h[i], 'Status'] = df_res.loc[idx_g[i], 'Status'] = 'ERRO NO AUTO'
                    df_res.loc[idx_h[i], 'ID_Match'] = df_res.loc[idx_g[i], 'ID_Match'] = f'#{id_count}'
                    id_count += 1
                    
            df_res = df_res.drop(columns=['K_H', 'K_G'])

            # REGRA "A VERIFICAR"
            df_res.loc[(df_res['Status'] == 'Falta na Getnet') & (df_res['Modalidade_H'].astype(str).str.upper() == 'HOTEL TRANSFERENCIA/PIX MANUAL'), 'Status'] = 'A VERIFICAR'

            # Ordenação e Limpeza
            mapa_ordem = {'Falta na Getnet':1, 'Falta no HITS':2, 'ERRO NO AUTO':3, 'A VERIFICAR':4, 'Divergência':5, 'Batido - OK':6}
            df_res['Ordem'] = df_res['Status'].map(mapa_ordem).fillna(99)
            df_res = df_res.sort_values(by=['Ordem', 'ID_Match', 'Data_H']).reset_index(drop=True)
            
            cols_f = ['ID_Match', 'Status', 'Pagamento', 'Valor_H', 'Valor_G', 'Auto', 'CV_H', 'CV_G', 'Data_H', 'Data_G', 'Modalidade_H', 'Modalidade_G', 'Usuário']
            df_res = df_res[[c for c in cols_f if c in df_res.columns]].fillna('')
            for c in df_res.columns: df_res[c] = df_res[c].apply(lambda x: '' if str(x).strip().lower() in ['none', 'nan', 'nat', '<na>'] else x)

            # --- PINTURA CIRÚRGICA (TELA) ---
            def cor_tela(row):
                est = [''] * len(row) # Fundo limpo (Branco)
                cols = list(row.index)
                st = row['Status']
                
                if st == 'Batido - OK': est = ['background-color: #e6ffed'] * len(row)
                elif st == 'Falta na Getnet':
                    for c in ['Pagamento', 'Valor_H', 'Auto', 'CV_H', 'Data_H', 'Modalidade_H', 'Usuário']:
                        if c in cols: est[cols.index(c)] = 'background-color: #ffeef0'
                elif st == 'Falta no HITS':
                    for c in ['Valor_G', 'CV_G', 'Data_G', 'Modalidade_G']:
                        if c in cols: est[cols.index(c)] = 'background-color: #ffeef0'
                elif st == 'A VERIFICAR':
                    if 'Status' in cols: est[cols.index('Status')] = 'background-color: #d0ebff; font-weight: bold; color: #004085;'
                elif st == 'Divergência':
                    if str(row['CV_H']) != str(row['CV_G']):
                        if 'CV_H' in cols: est[cols.index('CV_H')] = 'background-color: #ffb067; font-weight: bold;'
                        if 'CV_G' in cols: est[cols.index('CV_G')] = 'background-color: #ffb067; font-weight: bold;'
                    if not np.isclose(float(row['Valor_H'] or 0), float(row['Valor_G'] or 0), atol=0.01):
                        if 'Valor_H' in cols: est[cols.index('Valor_H')] = 'background-color: #ffb067; font-weight: bold;'
                        if 'Valor_G' in cols: est[cols.index('Valor_G')] = 'background-color: #ffb067; font-weight: bold;'
                elif st == 'ERRO NO AUTO':
                    if 'ID_Match' in cols: est[cols.index('ID_Match')] = 'background-color: #fce83a; font-weight: bold; color: black;'
                    if 'Auto' in cols: est[cols.index('Auto')] = 'background-color: #ffb067; font-weight: bold;'
                return est

            # --- DASHBOARD ---
            st.success("✅ Conciliação Realizada!")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total", len(df_res))
            c2.metric("OK", len(df_res[df_res['Status'] == 'Batido - OK']))
            c3.metric("Faltas", len(df_res[df_res['Status'].str.contains('Falta')]))
            c4.metric("Inconsistências", len(df_res[df_res['Status'].isin(['Divergência', 'ERRO NO AUTO'])]))
            c5.metric("A Verificar", len(df_res[df_res['Status'] == 'A VERIFICAR']))

            st.dataframe(df_res.style.apply(cor_tela, axis=1).format({'Valor_H': formata_moeda, 'Valor_G': formata_moeda}), use_container_width=True)

            # --- EXPORTAÇÃO EXCEL PROFISSIONAL (Pintura Cirúrgica, AutoFit e Filtros) ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, index=False, sheet_name='Resultado')
                ws = writer.sheets['Resultado']
                
                # Configurações de UX do Excel
                ws.freeze_panes = 'A2' # Congela o cabeçalho
                ws.auto_filter.ref = ws.dimensions # Ativa os filtros
                
                # Auto-Ajuste de Largura das Colunas
                for column in ws.columns:
                    max_length = 0
                    col_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
                        except: pass
                    ws.column_dimensions[col_letter].width = min((max_length + 2), 35)

                # Cores
                f_ok = PatternFill("solid", "E6FFED")
                f_red = PatternFill("solid", "FFEEF0")
                f_org = PatternFill("solid", "FFB067")
                f_blu = PatternFill("solid", "D0EBFF")
                f_ylw = PatternFill("solid", "FCE83A")
                
                idx = {n: i for i, n in enumerate(df_res.columns, 1)}

                for r in range(2, ws.max_row + 1):
                    st_v = ws.cell(r, idx['Status']).value
                    
                    # Formatação Moeda Contábil
                    for c_n in ['Valor_H', 'Valor_G']:
                        if c_n in idx and ws.cell(r, idx[c_n]).value != '':
                            ws.cell(r, idx[c_n]).number_format = '"R$" #,##0.00'
                    
                    # Pintura Cirúrgica
                    if st_v == 'Batido - OK':
                        for c in range(1, ws.max_column + 1): ws.cell(r, c).fill = f_ok
                    elif st_v == 'Falta na Getnet':
                        for c_n in ['Pagamento', 'Valor_H', 'Auto', 'CV_H', 'Data_H', 'Modalidade_H', 'Usuário']:
                            if c_n in idx: ws.cell(r, idx[c_n]).fill = f_red
                    elif st_v == 'Falta no HITS':
                        for c_n in ['Valor_G', 'CV_G', 'Data_G', 'Modalidade_G']:
                            if c_n in idx: ws.cell(r, idx[c_n]).fill = f_red
                    elif st_v == 'A VERIFICAR':
                        ws.cell(r, idx['Status']).fill = f_blu
                    elif st_v == 'ERRO NO AUTO':
                        if 'ID_Match' in idx: ws.cell(r, idx['ID_Match']).fill = f_ylw
                        if 'Auto' in idx: ws.cell(r, idx['Auto']).fill = f_org
                    elif st_v == 'Divergência':
                        if str(ws.cell(r, idx['CV_H']).value) != str(ws.cell(r, idx['CV_G']).value):
                            if 'CV_H' in idx: ws.cell(r, idx['CV_H']).fill = f_org
                            if 'CV_G' in idx: ws.cell(r, idx['CV_G']).fill = f_org
                        if not np.isclose(float(ws.cell(r, idx['Valor_H']).value or 0), float(ws.cell(r, idx['Valor_G']).value or 0), atol=0.01):
                            if 'Valor_H' in idx: ws.cell(r, idx['Valor_H']).fill = f_org
                            if 'Valor_G' in idx: ws.cell(r, idx['Valor_G']).fill = f_org
            
            st.download_button("📥 BAIXAR RESULTADO (.xlsx)", output.getvalue(), "conciliacao_pro.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.info("💡 Dica: Arraste os arquivos acima para começar.")
