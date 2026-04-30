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

# 2. CSS CUSTOMIZADO (Design Moderno e Correção de Cores)
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
    .stFileUploader:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); }

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
            
            if 'STATUS DA TRANSAÇÃO' in df_g_cartoes.columns:
                df_g_cartoes = df_g_cartoes[df_g_cartoes['STATUS DA TRANSAÇÃO'].str.contains('Aprovada', case=False, na=False)]
            
            # Alterado Doc_G para CV_G
            df_g_cartoes = df_g_cartoes.rename(columns={
                'NÚMERO DE AUTORIZAÇÃO (AUT)': 'Auto', 'NÚMERO DO COMPROVANTE DE VENDAS (CV)': 'CV_G',
                'VALOR BRUTO': 'Valor_G', 'DATA/HORA DA VENDA': 'Data_G', 'MODALIDADE': 'Mod_G', 'BANDEIRA': 'Band_G'
            })
            df_g_cartoes = df_g_cartoes[~df_g_cartoes['Mod_G'].astype(str).str.upper().str.contains('GET ECO', na=False)]
            df_g_cartoes['Modalidade_G'] = df_g_cartoes['Band_G'].astype(str) + " " + df_g_cartoes['Mod_G'].astype(str)

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
                    'Modalidade_G': 'GETNET PIX', 'Auto': 'PIX_SEM_AUT', 'CV_G': ''
                })

            # --- 2. PROCESSAMENTO HITS ---
            df_hits = ler_excel_inteligente(hits_file, 'Autorização')
            df_hits.columns = df_hits.columns.astype(str).str.strip()
            # Alterado Doc_H para CV_H
            df_hits = df_hits.rename(columns={
                'Autorização': 'Auto', 'Documento': 'CV_H', 'Valor': 'Valor_H', 
                'Data': 'Data_H', 'Pagamento': 'Pagamento', 'Tipo de Pagamento': 'Modalidade_H'
            })
            
            filtro_h = 'FATURADO|DINHEIRO|GET ECO'
            df_hits = df_hits[~df_hits['Modalidade_H'].astype(str).str.upper().str.contains(filtro_h, regex=True)]

            # --- 3. CRUZAMENTOS ---
            mask_pix_h = df_hits['Modalidade_H'].astype(str).str.upper().str.contains('PIX', na=False)
            df_h_pix = df_hits[mask_pix_h].copy()
            df_h_cart = df_hits[~mask_pix_h].copy()

            for df in [df_h_cart, df_g_cartoes]:
                df['Auto'] = df['Auto'].astype(str).str.strip().str.upper()
                v_col = 'Valor_H' if 'Valor_H' in df.columns else 'Valor_G'
                df[v_col] = garantir_numero(df[v_col])

            df_m_cart = pd.merge(df_h_cart, df_g_cartoes[['Auto', 'CV_G', 'Valor_G', 'Data_G', 'Modalidade_G']], on='Auto', how='outer', indicator=True)

            if not df_g_pix.empty:
                df_h_pix['Valor_H'] = garantir_numero(df_h_pix['Valor_H'])
                df_g_pix['Valor_G'] = garantir_numero(df_g_pix['Valor_G'])
                df_h_pix['Match'] = df_h_pix.groupby(df_h_pix['Valor_H'].round(2)).cumcount()
                df_g_pix['Match'] = df_g_pix.groupby(df_g_pix['Valor_G'].round(2)).cumcount()
                df_m_pix = pd.merge(df_h_pix, df_g_pix, left_on=['Valor_H', 'Match'], right_on=['Valor_G', 'Match'], how='outer', indicator=True).drop(columns=['Match'])
            else:
                df_h_pix['_merge'] = 'left_only'
                df_m_pix = df_h_pix

            # --- 4. TRATAMENTO FINAL DOS DADOS (LIMPEZA VISUAL) ---
            df_res = pd.concat([df_m_cart, df_m_pix], ignore_index=True)
            cond = [(df_res['_merge']=='left_only'), (df_res['_merge']=='right_only'), (df_res['_merge']=='both')]
            df_res['Status'] = np.select(cond, ['Falta na Getnet', 'Falta no HITS', 'Batido - OK'], default='Divergência')
            
            # Limpeza do .0 indesejado nas colunas CV
            df_res['CV_H'] = df_res['CV_H'].astype(str).str.replace(r'\.0$', '', regex=True)
            df_res['CV_G'] = df_res['CV_G'].astype(str).str.replace(r'\.0$', '', regex=True)

            # Limpeza da Data e Hora
            df_res['Data_H'] = pd.to_datetime(df_res['Data_H'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
            df_res['Data_G'] = pd.to_datetime(df_res['Data_G'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')

            df_res['Ordem'] = df_res['Status'].map({'Falta na Getnet':1, 'Falta no HITS':2, 'Divergência':3, 'Batido - OK':4})
            df_res = df_res.sort_values(by=['Ordem', 'Pagamento'])
            
            cols_final = ['Status', 'Pagamento', 'Valor_H', 'Valor_G', 'Auto', 'CV_H', 'CV_G', 'Data_H', 'Data_G', 'Modalidade_H', 'Modalidade_G']
            df_res = df_res[[c for c in cols_final if c in df_res.columns]].reset_index(drop=True)

            # Limpeza de dados vazios (Remove a palavra "None" e "nan" da tela)
            df_res = df_res.fillna('')
            df_res = df_res.replace(['None', 'nan', 'NaN', 'NaT'], '')

            # --- NOVA LÓGICA INTELIGENTE DE CORES (NA TELA) ---
            def aplicar_cores_tela(row):
                # Cores de fundo da linha
                if row['Status'] == 'Batido - OK': estilos = ['background-color: #e6ffed'] * len(row)
                elif row['Status'] in ['Falta na Getnet', 'Falta no HITS']: estilos = ['background-color: #ffeef0'] * len(row)
                else: estilos = ['background-color: #fff8e6'] * len(row)
                
                # Se estiver em ambas as planilhas, procura onde a divergência ocorreu (Raio-X)
                if row['Status'] not in ['Falta na Getnet', 'Falta no HITS']:
                    cols = list(row.index)
                    cv_h, cv_g = str(row['CV_H']).strip(), str(row['CV_G']).strip()
                    if cv_h and cv_g and cv_h != cv_g:
                        estilos[cols.index('CV_H')] = 'background-color: #ffb067; color: black; font-weight: bold;'
                        estilos[cols.index('CV_G')] = 'background-color: #ffb067; color: black; font-weight: bold;'
                    
                    try:
                        v_h, v_g = float(row['Valor_H'] or 0), float(row['Valor_G'] or 0)
                        if not np.isclose(v_h, v_g, atol=0.01):
                            estilos[cols.index('Valor_H')] = 'background-color: #ffb067; color: black; font-weight: bold;'
                            estilos[cols.index('Valor_G')] = 'background-color: #ffb067; color: black; font-weight: bold;'
                    except: pass
                return estilos

            # --- DASHBOARDS UI ---
            st.success("✅ Conciliação Realizada com Sucesso!")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Transações", len(df_res))
            m2.metric("Conciliados (OK)", len(df_res[df_res['Status'] == 'Batido - OK']))
            m3.metric("Pendências", len(df_res[df_res['Status'] != 'Batido - OK']))

            # Exibição na Tela com formatação R$ via Streamlit
            st.dataframe(
                df_res.style.apply(aplicar_cores_tela, axis=1),
                column_config={
                    "Valor_H": st.column_config.NumberColumn("Valor H", format="R$ %.2f"),
                    "Valor_G": st.column_config.NumberColumn("Valor G", format="R$ %.2f")
                },
                use_container_width=True
            )

            # --- EXCEL EXPORT BLINDADO COM ALERTA ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, index=False, sheet_name='Resultado')
                ws = writer.sheets['Resultado']
                
                green_fill = PatternFill(start_color="E6FFED", end_color="E6FFED", fill_type="solid")
                red_fill = PatternFill(start_color="FFEEF0", end_color="FFEEF0", fill_type="solid")
                orange_fill = PatternFill(start_color="FFB067", end_color="FFB067", fill_type="solid")
                
                col_idx = {col_name: idx for idx, col_name in enumerate(df_res.columns, 1)}

                for row in range(2, ws.max_row + 1):
                    status_val = ws.cell(row=row, column=col_idx['Status']).value
                    base_fill = green_fill if status_val == 'Batido - OK' else red_fill
                    
                    # Pinta a linha
                    for col in range(1, ws.max_column + 1): 
                        ws.cell(row=row, column=col).fill = base_fill

                    # Aplica a formatação Contábil/Moeda R$ nativa do Excel para as colunas numéricas
                    if 'Valor_H' in col_idx and ws.cell(row=row, column=col_idx['Valor_H']).value != '':
                        ws.cell(row=row, column=col_idx['Valor_H']).number_format = '"R$" #,##0.00'
                    if 'Valor_G' in col_idx and ws.cell(row=row, column=col_idx['Valor_G']).value != '':
                        ws.cell(row=row, column=col_idx['Valor_G']).number_format = '"R$" #,##0.00'

                    # Sobrescreve as cores para Laranja em caso de divergência específica
                    if status_val not in ['Falta na Getnet', 'Falta no HITS']:
                        cv_h = str(ws.cell(row=row, column=col_idx['CV_H']).value or '').strip()
                        cv_g = str(ws.cell(row=row, column=col_idx['CV_G']).value or '').strip()
                        if cv_h and cv_g and cv_h != cv_g:
                            ws.cell(row=row, column=col_idx['CV_H']).fill = orange_fill
                            ws.cell(row=row, column=col_idx['CV_G']).fill = orange_fill
                        
                        try:
                            val_h = float(ws.cell(row=row, column=col_idx['Valor_H']).value or 0)
                            val_g = float(ws.cell(row=row, column=col_idx['Valor_G']).value or 0)
                            if not np.isclose(val_h, val_g, atol=0.01):
                                ws.cell(row=row, column=col_idx['Valor_H']).fill = orange_fill
                                ws.cell(row=row, column=col_idx['Valor_G']).fill = orange_fill
                        except: pass
            
            # Botão de download com declaração forte do tipo de arquivo (.xlsx)
            st.download_button(
                label="📥 BAIXAR PLANILHA DE RESULTADOS (.xlsx)",
                data=output.getvalue(),
                file_name="resultado_conciliador_formatado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("💡 Dica: Exporte os relatórios de hoje e arraste-os para as caixas acima para começar.")
