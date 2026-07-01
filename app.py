import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import plotly.express as px  

# Importações para o Google APIs
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# Importações para o PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuração da página
st.set_page_config(page_title="Sistema de Verificação - Academias", layout="wide")

# =========================================================================
# CONFIGURAÇÕES OBRIGATÓRIAS DO GOOGLE
# =========================================================================
# APAGUE O TEXTO ABAIXO E COLE O ID DA SUA PLANILHA:
ID_PLANILHA_GOOGLE = https://docs.google.com/spreadsheets/d/1JrUGFV8cwRR7niP3y95UMg8Q5nbj9adGjrkvnDzJon4/edit?usp=sharing

# ESTE É O ID DA SUA PASTA QUE VOCÊ ME MANDOU:
ID_PASTA_FOTOS_DRIVE = https://drive.google.com/drive/folders/1DQwCGlv7DM-WOmw__WkpwbxVc7VhtcvK?usp=drive_link
# =========================================================================

# Lista de academias
bairros = [
    'Feira X', 'Fraga Maia', 'Muchila', 'Vila Olimpia', 
    'Artemia', 'Sobradinho', 'Noide', 'Cidade Nova', 
    'Adenil', 'Presidente', 'Jardim Europa'
]

# Inicializa as conexões com o Google de forma segura
@st.cache_resource
def inicializar_conexoes_google():
    # Procura as credenciais nos Secrets do Streamlit Cloud
    creds_dict = st.secrets["google_credentials"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    client_gspread = gspread.authorize(creds)
    client_drive = build('drive', 'v3', credentials=creds)
    return client_gspread, client_drive

try:
    client_gspread, client_drive = inicializar_conexoes_google()
    sheet = client_gspread.open_by_key(ID_PLANILHA_GOOGLE).sheet1
except Exception as e:
    st.error("Erro ao conectar com as APIs do Google. Verifique os IDs e as Credenciais.")
    st.stop()

# Funções auxiliares para o Google Drive
def criar_subpasta_drive(nome_pasta, parent_id):
    query = f"name = '{nome_pasta}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    existente = client_drive.files().list(q=query, fields="files(id)").execute().get('files', [])
    if existente:
        return existente[0]['id']
    
    metadata = {
        'name': nome_pasta,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    pasta = client_drive.files().create(body=metadata, fields='id').execute()
    return pasta.get('id')

def descarregar_foto_drive(file_id):
    request = client_drive.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh

def listar_fotos_subpasta(folder_id):
    if not folder_id or folder_id == "nan" or folder_id == "":
        return []
    query = f"'{folder_id}' in parents and mimeType label='image' and trashed = false"
    try:
        results = client_drive.files().list(q=query, fields="files(id, name)").execute()
        return results.get('files', [])
    except Exception:
        return []

def apagar_fotos_subpasta(folder_id):
    fotos = listar_fotos_subpasta(folder_id)
    for foto in fotos:
        client_drive.files().delete(fileId=foto['id']).execute()

def obter_dados_sheet():
    dados = sheet.get_all_records()
    if dados:
        return pd.DataFrame(dados)
    return pd.DataFrame(columns=["Data", "Academia", "Teve Erro?", "Descricao Erro", "Solucao", "Pasta Fotos"])

# ==========================================
# FUNÇÃO PARA GERAR O PDF COM AS FOTOS
# ==========================================
def gerar_pdf(df_dados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor('#1E3A8A'), spaceAfter=20, alignment=1)
    date_style = ParagraphStyle('DateStyle', parent=styles['Heading2'], fontSize=13, leading=16, textColor=colors.HexColor('#0F766E'), spaceBefore=14, spaceAfter=6)
    header_table_style = ParagraphStyle('HeaderTableStyle', parent=styles['Normal'], fontSize=10, leading=12, textColor=colors.white, fontName='Helvetica-Bold')
    body_table_style = ParagraphStyle('BodyTableStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.black)
    
    story.append(Paragraph("🏋️ Relatório Diário de Verificação de Academias", title_style))
    story.append(Spacer(1, 10))
    
    if not df_dados.empty:
        datas = sorted(df_dados["Data"].unique(), reverse=True)
        for data in datas:
            story.append(Paragraph(f"📅 Data: {data}", date_style))
            df_dia = df_dados[df_dados["Data"] == data]
            
            table_data = [[
                Paragraph("Academia", header_table_style),
                Paragraph("Erro?", header_table_style),
                Paragraph("Descrição", header_table_style),
                Paragraph("Solução", header_table_style),
                Paragraph("Print", header_table_style)
            ]]
            
            for _, row in df_dia.iterrows():
                desc = str(row["Descricao Erro"]) if pd.notna(row["Descricao Erro"]) and str(row["Descricao Erro"]).strip() != "" else "-"
                sol = str(row["Solucao"]) if pd.notna(row["Solucao"]) and str(row["Solucao"]).strip() != "" else "-"
                
                foto_celula = Paragraph("-", body_table_style)
                pasta_fotos_id = str(row["Pasta Fotos"])
                
                arquivos = listar_fotos_subpasta(pasta_fotos_id)
                if arquivos:
                    try:
                        img_bytes = descarregar_foto_drive(arquivos[0]['id'])
                        with Image.open(img_bytes) as pil_img:
                            w, h = pil_img.size
                            aspect = w / float(h)
                            new_h = 60
                            new_w = new_h * aspect
                            if new_w > 100: 
                                new_w = 100
                                new_h = new_w / aspect
                        img_bytes.seek(0)
                        foto_celula = RLImage(img_bytes, width=new_w, height=new_h)
                    except Exception:
                        foto_celula = Paragraph("(Erro)", body_table_style)
                
                table_data.append([
                    Paragraph(str(row["Academia"]), body_table_style),
                    Paragraph(str(row["Teve Erro?"]), body_table_style),
                    Paragraph(desc, body_table_style),
                    Paragraph(sol, body_table_style),
                    foto_celula
                ])
            
            t = Table(table_data, colWidths=[80, 40, 150, 150, 115])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
                ('ALIGN', (4,1), (4,-1), 'CENTER'), 
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
            ]))
            story.append(t)
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("Nenhum registro encontrado.", body_table_style))
        
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================
st.title("🏋️‍♂️ Verificação Diária de Academias")

aba_registrar, aba_visualizar, aba_modificar, aba_prints, aba_dashboard = st.tabs([
    "📝 Registrar Verificação", 
    "📊 Ver Histórico", 
    "✏️ Modificar", 
    "🖼️ Ver Prints", 
    "📈 Estatísticas"
])

# ==========================================
# ABA 1: REGISTRAR
# ==========================================
with aba_registrar:
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            academia_selecionada = st.selectbox("Qual academia você está verificando?", bairros)
            teve_erro = st.radio("Apresentou algum erro?", ["Não", "Sim"])
            
        with col2:
            st.info("Se não houver erro, os campos abaixo serão salvos automaticamente como 'Tudo OK'.")
            descricao_erro = st.text_area("Descrição do Erro (se houver):")
            solucao = st.text_area("Solução Aplicada/Proposta:")
            
        fotos_upload = st.file_uploader("Anexe prints ou fotos (Opcional)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        botao_salvar = st.form_submit_button("Salvar Registro")
        
        if botao_salvar:
            hoje = datetime.now().strftime("%Y-%m-%d")
            id_subpasta = ""
            
            if fotos_upload:
                id_pasta_data = criar_subpasta_drive(hoje, ID_PASTA_FOTOS_DRIVE)
                id_subpasta = criar_subpasta_drive(academia_selecionada, id_pasta_data)
                
                for foto in fotos_upload:
                    media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype=foto.type, resumable=True)
                    meta = {'name': foto.name, 'parents': [id_subpasta]}
                    client_drive.files().create(body=meta, media_body=media).execute()
            
            desc_salvar = "Tudo OK" if teve_erro == "Não" else descricao_erro
            sol_salvar = "Tudo OK" if teve_erro == "Não" else solucao

            sheet.append_row([hoje, academia_selecionada, teve_erro, desc_salvar, sol_salvar, id_subpasta])
            st.success(f"Registro de {academia_selecionada} salvo com sucesso no Google Sheets!")
            st.rerun()

# ==========================================
# ABA 2: VISUALIZAR E PESQUISAR
# ==========================================
with aba_visualizar:
    st.subheader("🔍 Filtros de Pesquisa")
    df = obter_dados_sheet()
    
    if not df.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            lista_academias = ["Todas"] + list(df["Academia"].unique())
            filtro_academia = st.selectbox("Filtrar por Academia:", lista_academias)
        with col_f2:
            lista_datas = ["Todas"] + list(df["Data"].unique())
            filtro_data = st.selectbox("Filtrar por Data:", lista_datas)
            
        df_filtrado = df.copy()
        if filtro_academia != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Academia"] == filtro_academia]
        if filtro_data != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Data"] == filtro_data]

        st.divider()

        if not df_filtrado.empty:
            pdf_em_bytes = gerar_pdf(df_filtrado)
            st.download_button(
                label="📥 Baixar Relatório Filtrado em PDF",
                data=pdf_em_bytes,
                file_name=f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )
            
            datas_unicas = sorted(df_filtrado["Data"].unique(), reverse=True)
            for data in datas_unicas:
                st.header(f"📅 {data}")
                df_dia = df_filtrado[df_filtrado["Data"] == data].copy()
                st.dataframe(df_dia.drop(columns=["Data"]), use_container_width=True)
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("O histórico está vazio.")

# ==========================================
# ABA 3: MODIFICAR / EDITAR
# ==========================================
with aba_modificar:
    st.subheader("✏️ Modificar / Editar Registro")
    df = obter_dados_sheet()
    
    if not df.empty:
        sufixo_erro_ed = df["Teve Erro?"].map({"Sim": " (Com Erro)", "Não": " (OK)"}).fillna("")
        opcoes_edicao = df["Data"].astype(str) + " - " + df["Academia"] + sufixo_erro_ed
        dict_edicao = dict(zip(opcoes_edicao, df.index))
        
        registro_selecionado = st.selectbox("Escolha qual registro deseja alterar:", list(dict_edicao.keys()), key="sb_edicao")
        indice_df = dict_edicao[registro_selecionado]
        dados_atuais = df.loc[indice_df]
        
        # O gspread usa indexação baseada em 1 e a linha 1 são os cabeçalhos, logo: linha_sheet = index + 2
        linha_sheet = int(indice_df) + 2
        
        with st.form("form_edicao"):
            st.markdown(f"**Modificando registro de {dados_atuais['Academia']} feito em {dados_atuais['Data']}**")
            
            ed_col1, ed_col2 = st.columns(2)
            with ed_col1:
                ed_academia = st.selectbox("Academia:", bairros, index=bairros.index(dados_atuais['Academia']) if dados_atuais['Academia'] in bairros else 0)
                ed_teve_erro = st.radio("Apresentou algum erro?", ["Não", "Sim"], index=0 if dados_atuais['Teve Erro?'] == "Não" else 1)
            with ed_col2:
                ed_descricao = st.text_area("Descrição do Erro:", value=str(dados_atuais['Descricao Erro']))
                ed_solucao = st.text_area("Solução Aplicada/Proposta:", value=str(dados_atuais['Solucao']))
            
            st.markdown("📷 **Gerenciamento de Fotos:**")
            pasta_fotos_id_atual = str(dados_atuais["Pasta Fotos"])
            arqs_atuais = listar_fotos_subpasta(pasta_fotos_id_atual)
            
            sub_limpar_fotos = False
            if arqs_atuais:
                st.text(f"Fotos atuais no Drive ({len(arqs_atuais)} foto(s))")
                sub_limpar_fotos = st.checkbox("Substituir todas as fotos atuais no Drive pelas novas fotos abaixo?")
                
            ed_novas_fotos = st.file_uploader("Adicionar novas fotos:", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="upload_edicao")
            
            col_btn_ed1, col_btn_ed2 = st.columns([1, 4])
            with col_btn_ed1:
                btn_salvar_edicao = st.form_submit_button("Salvar Alterações", type="primary")
            with col_btn_ed2:
                btn_deletar_registro = st.form_submit_button("🚨 Excluir Este Registro")

            if btn_salvar_edicao:
                nova_pasta_id = pasta_fotos_id_atual
                
                if (not nova_pasta_id or nova_pasta_id == "nan" or nova_pasta_id == "") and ed_novas_fotos:
                    id_pasta_data = criar_subpasta_drive(str(dados_atuais['Data']), ID_PASTA_FOTOS_DRIVE)
                    nova_pasta_id = criar_subpasta_drive(ed_academia, id_pasta_data)
                
                if nova_pasta_id and nova_pasta_id != "nan" and nova_pasta_id != "":
                    if sub_limpar_fotos:
                        apagar_fotos_subpasta(nova_pasta_id)
                    
                    for foto in ed_novas_fotos:
                        media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype=foto.type, resumable=True)
                        meta = {'name': foto.name, 'parents': [nova_pasta_id]}
                        client_drive.files().create(body=meta, media_body=media).execute()

                # Atualiza no Google Sheets (Linha correspondente)
                valores_atualizados = [str(dados_atuais['Data']), ed_academia, ed_teve_erro, ed_descricao, ed_solucao, nova_pasta_id]
                sheet.update(range_name=f"A{linha_sheet}:F{linha_sheet}", values=[valores_atualizados])
                
                st.success("Registro modificado com sucesso no Google Sheets!")
                st.rerun()
            
            if btn_deletar_registro:
                sheet.delete_rows(linha_sheet)
                st.warning("Registro excluído com sucesso do Google Sheets!")
                st.rerun()
    else:
         st.info("O histórico está vazio.")

# ==========================================
# ABA 4: VER PRINTS
# ==========================================
with aba_prints:
    st.subheader("🖼️ Ver Prints e Comprovantes")
    df = obter_dados_sheet()
    
    if not df.empty:
        df_com_fotos = df[(df["Pasta Fotos"].notna()) & (df["Pasta Fotos"].astype(str) != "") & (df["Pasta Fotos"].astype(str) != "nan")]
        if not df_com_fotos.empty:
            sufixo_erro = df_com_fotos["Teve Erro?"].map({"Sim": " (Com Erro)", "Não": " (OK)"}).fillna("")
            opcoes_fotos = df_com_fotos["Data"].astype(str) + " - " + df_com_fotos["Academia"] + sufixo_erro
            dict_opcoes = dict(zip(opcoes_fotos, df_com_fotos.index))
            
            foto_selecionada = st.selectbox("Selecione o registro para ver as fotos:", list(dict_opcoes.keys()))
            indice_sel = dict_opcoes[foto_selecionada]
            pasta_fotos_id_sel = df_com_fotos.loc[indice_sel, "Pasta Fotos"]
            
            arquivos = listar_fotos_subpasta(pasta_fotos_id_sel)
            if arquivos:
                cols = st.columns(3)
                for i, arquivo in enumerate(arquivos):
                    try:
                        img_bytes = descarregar_foto_drive(arquivo['id'])
                        img = Image.open(img_bytes)
                        cols[i % 3].image(img, caption=arquivo['name'], use_container_width=True)
                    except Exception:
                        pass
            else:
                st.info("Nenhuma foto encontrada para este registro no Google Drive.")
        else:
            st.info("Nenhuma foto/comprovante foi anexado até o momento.")
    else:
         st.info("O histórico está vazio.")

# ==========================================
# ABA 5: DASHBOARD E ESTATÍSTICAS
# ==========================================
with aba_dashboard:
    st.subheader("📈 Análise de Dados das Academias")
    df_dash = obter_dados_sheet()
    
    if not df_dash.empty:
        contagem_geral = df_dash['Academia'].value_counts().reset_index()
        contagem_geral.columns = ['Academia', 'Total de Registros']
        
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            st.markdown("### 📊 Participação (%) de cada Academia")
            fig_pizza = px.pie(contagem_geral, names='Academia', values='Total de Registros', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pizza.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pizza, use_container_width=True)
            
            mais_visitada = contagem_geral.iloc[0]
            menos_visitada = contagem_geral.iloc[-1]
            st.success(f"**Mais Frequente:** {mais_visitada['Academia']} ({mais_visitada['Total de Registros']} registros)")
            st.warning(f"**Menos Frequente:** {menos_visitada['Academia']} ({menos_visitada['Total de Registros']} registros)")
            
        with col_grafico2:
            st.markdown("### 🚨 Academias com Mais Erros")
            df_erros = df_dash[df_dash['Teve Erro?'] == 'Sim']
            
            if not df_erros.empty:
                contagem_erros = df_erros['Academia'].value_counts().reset_index()
                contagem_erros.columns = ['Academia', 'Quantidade de Erros']
                
                fig_barras = px.bar(contagem_erros, x='Academia', y='Quantidade de Erros', color='Quantidade de Erros', color_continuous_scale='Reds', text_auto=True)
                fig_barras.update_layout(xaxis_title="Academia", yaxis_title="Nº de Erros")
                st.plotly_chart(fig_barras, use_container_width=True)
                
                pior_academia = contagem_erros.iloc[0]
                st.error(f"**Atenção:** {pior_academia['Academia']} é a academia com mais problemas registrados ({pior_academia['Quantidade de Erros']} erros).")
            else:
                st.info("🎉 Parabéns! Nenhum erro foi registrado até o momento.")
    else:
        st.info("O sistema ainda não possui dados suficientes para gerar os gráficos.")
