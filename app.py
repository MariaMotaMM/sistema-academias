import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import base64
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from PIL import Image

# Configuração da página
st.set_page_config(page_title="Sistema de Verificação - Academias", layout="wide")

if "aba_ativa" not in st.session_state:
    st.session_state.aba_ativa = 0

# ID da Planilha
ID_PLANILHA_GOOGLE = "1JrUGFV8cwRR7niP3y95UMg8Q5nbj9adGjrkvnDzJon4"
bairros = ['Feira X', 'Fraga Maia', 'Muchila', 'Vila Olimpia', 'Artemia', 'Sobradinho', 'Noide', 'Cidade Nova', 'Adenil', 'Presidente', 'Jardim Europa']

@st.cache_resource
def conectar_google():
    creds_dict = st.secrets["google_credentials"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds).open_by_key(ID_PLANILHA_GOOGLE).sheet1

sheet = conectar_google()

def obter_data_hoje():
    return date.today().strftime("%Y-%m-%d")

def obter_dados_sheet():
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        df["_idx"] = df.index + 2 
    return df

# --- FUNÇÃO DE FOTO OTIMIZADA E SEGURA ---
def foto_para_base64_otimizada(foto_file):
    """
    Mantém a qualidade de leitura (800px) e reduz o "peso" em texto para caber no Google Sheets.
    """
    img = Image.open(foto_file)
    
    # Converte para RGB se for PNG transparente
    if img.mode in ("RGBA", "P"): 
        img = img.convert("RGB")
        
    # Redimensiona mantendo a proporção, com limite de 800px (ótimo para ler textos)
    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    
    buffered = io.BytesIO()
    # Salva com compressão otimizada
    img.save(buffered, format="JPEG", quality=75, optimize=True)
    
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- INTERFACE ---
st.title("🏋️‍♂️ Verificação de Academias")

lista_abas = ["📝 Registrar", "📊 Histórico", "✏️ Modificar", "🖼️ Ver Prints", "📈 Dashboard"]
aba_registrar, aba_visualizar, aba_modificar, aba_prints, aba_dash = st.tabs(lista_abas)

# ==================== ABA REGISTRAR ====================
with aba_registrar:
    with st.form("form_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            acad = st.selectbox("Academia", bairros, key="reg_acad")
            erro = st.radio("Apresentou erro?", ["Não", "Sim"], key="reg_erro")
        with col2:
            desc = st.text_area("Descrição", value="Tudo OK", key="reg_desc")
            sol = st.text_area("Solução", value="Tudo OK", key="reg_sol")
            
        fotos = st.file_uploader("Fotos", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="reg_fotos")
        
        botão_salvar = st.form_submit_button("Salvar")
        
    if botão_salvar:
        if not fotos:
            with st.spinner("Salvando registro..."):
                sheet.append_row([obter_data_hoje(), acad, erro, desc, sol, ""])
            st.success("Registro salvo com sucesso!")
            st.rerun()
        else:
            with st.spinner("Otimizando e verificando tamanho das fotos..."):
                fotos_b64 = [foto_para_base64_otimizada(f) for f in fotos]
                string_fotos = "|".join(fotos_b64)
                
                if len(string_fotos) > 50000:
                    st.error(
                        f"🚨 Não foi possível salvar as imagens! O tamanho acumulado das fotos "
                        f"({len(string_fotos)} caracteres) excede o limite do Google Sheets (50.000 caracteres). "
                        "Tente enviar menos fotos por vez ou reduza o tamanho do arquivo original."
                    )
                else:
                    try:
                        sheet.append_row([obter_data_hoje(), acad, erro, desc, sol, string_fotos])
                        st.success("Registro salvo com sucesso!")
                        st.rerun()
                    except gspread.exceptions.APIError as e:
                        st.error(f"Erro na API do Google Sheets: {e}")

# ==================== ABA VISUALIZAR ====================
with aba_visualizar:
    st.subheader("🔍 Filtros de Pesquisa")
    df_vis = obter_dados_sheet()
    
    if not df_vis.empty:
        c1, c2 = st.columns(2)
        filtro_acad_v = c1.selectbox("Filtrar por Academia:", ["Todas"] + list(df_vis["Academia"].unique()), key="v_acad")
        filtro_data_v = c2.selectbox("Filtrar por Data:", ["Todas"] + list(df_vis["Data"].unique()), key="v_data")
        
        df_fv = df_vis.copy()
        if filtro_acad_v != "Todas": df_fv = df_fv[df_fv["Academia"] == filtro_acad_v]
        if filtro_data_v != "Todas": df_fv = df_fv[df_fv["Data"] == filtro_data_v]
        
        st.divider()
        
        if not df_fv.empty:
            datas_unicas = sorted(df_fv["Data"].unique(), reverse=True)
            
            # SOLUÇÃO AQUI: Em vez de st.tabs (que quebra o layout), usamos st.expander
            for data in datas_unicas:
                with st.expander(f"📅 Registros do dia: {data}", expanded=True):
                    df_exibicao = df_fv[df_fv["Data"] == data].drop(columns=["Fotos", "_idx"], errors="ignore")
                    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("O histórico está vazio.")

# ==================== ABA MODIFICAR ====================
with aba_modificar:
    st.subheader("✏️ Filtrar para Modificar")
    df_mod = obter_dados_sheet()
    
    if not df_mod.empty and "Academia" in df_mod.columns:
        c1, c2 = st.columns(2)
        filtro_acad_m = c1.selectbox("Filtrar Academia:", ["Todas"] + list(df_mod["Academia"].unique()), key="m_acad")
        filtro_data_m = c2.selectbox("Filtrar Data:", ["Todas"] + list(df_mod["Data"].unique()), key="m_data")
        
        df_fm = df_mod.copy()
        if filtro_acad_m != "Todas": df_fm = df_fm[df_fm["Academia"] == filtro_acad_m]
        if filtro_data_m != "Todas": df_fm = df_fm[df_fm["Data"] == filtro_data_m]
        
        if not df_fm.empty:
            opcoes_mod = df_fm.apply(lambda x: f"{x['Data']} - {x['Academia']} (ID:{x['_idx']})", axis=1).tolist()
            selecao_m = st.selectbox("Selecione o registro para editar/excluir:", ["Selecione um registro..."] + opcoes_mod, key="select_registro_edit")
            
            if selecao_m != "Selecione um registro...":
                idx = int(selecao_m.split("(ID:")[1].replace(")", ""))
                d = df_mod.loc[df_mod["_idx"] == idx].iloc[0]
                
                with st.form("edit_form_final", clear_on_submit=False):
                    e_a = st.selectbox("Academia", bairros, index=bairros.index(d['Academia']) if d['Academia'] in bairros else 0)
                    e_e = st.radio("Erro?", ["Não", "Sim"], index=0 if d['Teve Erro?']=="Não" else 1)
                    e_d = st.text_area("Descrição", value=d['Descricao Erro'])
                    e_s = st.text_area("Solução", value=d['Solucao'])
                    
                    c_btn1, c_btn2 = st.columns(2)
                    if c_btn1.form_submit_button("Atualizar"):
                        fotos_atuais = str(d.get('Fotos', ''))
                        sheet.update(f"A{idx}:F{idx}", [[obter_data_hoje(), e_a, e_e, e_d, e_s, fotos_atuais]])
                        st.success("Atualizado com sucesso!")
                        st.rerun()
                        
                    if c_btn2.form_submit_button("🚨 Excluir"):
                        sheet.delete_rows(idx)
                        st.success("Deletado com sucesso!")
                        st.rerun()
                st.info("💡 Após atualizar ou excluir, verifique a aba '📊 Histórico'.")
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("O histórico está vazio ou não possui os dados necessários.")

# ==================== ABA DASHBOARD ====================
with aba_dash:
    st.subheader("📈 Análise de Dados das Academias")
    df_dash_full = obter_dados_sheet()
    
    if not df_dash_full.empty and "Academia" in df_dash_full.columns:
        datas_disponiveis = ["Todas"] + sorted(df_dash_full["Data"].unique().tolist(), reverse=True)
        filtro_data_dash = st.selectbox("Filtrar Dashboard por Data:", datas_disponiveis, key="d_data")
        
        df_dash = df_dash_full.copy()
        if filtro_data_dash != "Todas":
            df_dash = df_dash[df_dash["Data"] == filtro_data_dash]

        if not df_dash.empty:
            contagem_real = df_dash['Academia'].value_counts().to_dict()
            dados_com_zero = {b: contagem_real.get(b, 0) for b in bairros}
            df_final = pd.DataFrame(list(dados_com_zero.items()), columns=['Academia', 'Total_Registros'])
            
            col_grafico1, col_grafico2 = st.columns(2)
            with col_grafico1:
                st.markdown("### 📊 Participação (%)")
                st.plotly_chart(px.pie(df_final, names='Academia', values='Total_Registros', hole=0.4), use_container_width=True)
            with col_grafico2:
                st.markdown("### 🚨 Mais Erros")
                df_erros = df_dash[df_dash['Teve Erro?'] == 'Sim']
                if not df_erros.empty:
                    contagem = df_erros['Academia'].value_counts().reset_index()
                    contagem.columns = ['Academia', 'Total_Erros']
                    st.plotly_chart(px.bar(contagem, x='Academia', y='Total_Erros', color='Total_Erros', color_continuous_scale='Reds', text_auto=True), use_container_width=True)
                else:
                    st.info("Nenhum erro registrado neste período.")

            st.divider()
            st.markdown("### 📉 Participação por Academia")
            df_ordenado = df_final.sort_values(by='Total_Registros', ascending=True)
            max_val = df_ordenado['Total_Registros'].max()
            fig_menor = px.bar(df_ordenado, x='Total_Registros', y='Academia', orientation='h', color='Total_Registros', color_continuous_scale='Blues', range_color=[0, max(1, max_val)], text_auto=True)
            fig_menor.update_traces(textfont_color='white')
            st.plotly_chart(fig_menor, use_container_width=True)
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
    else:
        st.info("Nenhum dado encontrado no histórico para gerar o Dashboard.")

# ==================== ABA PRINTS ====================
with aba_prints:
    st.subheader("🖼️ Filtros para Visualizar Prints")
    df_pr = obter_dados_sheet()
    
    if not df_pr.empty and "Fotos" in df_pr.columns:
        df_fp = df_pr[df_pr["Fotos"] != ""]
        
        if not df_fp.empty:
            col1, col2 = st.columns(2)
            f_acad_p = col1.selectbox("Filtrar Academia:", ["Todas"] + list(df_fp["Academia"].unique()), key="p_acad")
            f_data_p = col2.selectbox("Filtrar Data:", ["Todas"] + list(df_fp["Data"].unique()), key="p_data")
            
            if f_acad_p != "Todas": df_fp = df_fp[df_fp["Academia"] == f_acad_p]
            if f_data_p != "Todas": df_fp = df_fp[df_fp["Data"] == f_data_p]
            
            if not df_fp.empty:
                lista_opcoes = list(df_fp["Data"] + " - " + df_fp["Academia"] + " (ID:" + df_fp["_idx"].astype(str) + ")")
                opcoes_p = ["Selecione um registro..."] + lista_opcoes
                
                reg = st.selectbox("Selecione qual registro deseja visualizar:", opcoes_p, key="p_select")
                
                if reg != "Selecione um registro...":
                    idx = int(reg.split("(ID:")[1].replace(")", ""))
                    fotos_ids = str(df_fp.loc[df_fp["_idx"] == idx, "Fotos"].values[0])
                    
                    if fotos_ids and fotos_ids.strip() != "nan" and fotos_ids.strip() != "":
                        st.divider()
                        st.markdown(f"**Visualizando prints de:** {reg.split(' (ID')[0]}")
                        
                        for item in fotos_ids.split("|"):
                            item = item.strip()
                            if item and len(item) > 100:
                                st.image(base64.b64decode(item), use_container_width=True)
                    else:
                        st.info("Este registro não possui fotos anexadas ou ocorreu um erro ao salvá-las.")
            else:
                st.warning("Nenhum print encontrado com os filtros selecionados.")
        else:
            st.info("Ainda não há registros com fotos salvas no sistema.")
    else:
        st.info("O banco de dados está vazio ou a coluna de fotos não existe.")
