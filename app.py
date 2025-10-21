import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import base64
import os

# 
LOGO_FILENAME = "LOGO HORIZONTAL COM TRANSPARÊNCIA.png"
EXCEL_FILE = "Calculadora_Diárias_CS.xlsx"

# Rodape + icone da logo
st.set_page_config(
    page_title="Calculadora de Diárias - IPAM",
    page_icon=LOGO_FILENAME,
    layout="centered"
)


# Função para converter imagem em base64  
def image_file_to_base64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        return None

logo_b64 = image_file_to_base64(LOGO_FILENAME)


if os.path.exists(LOGO_FILENAME):
  
    _, mid, _ = st.columns([1, 6, 1])
    with mid:
        st.image(LOGO_FILENAME, width=120)
        st.markdown("<h1 style='margin-top: 6px; text-align:center;'>Calculadora de Diárias - IPAM</h1>", unsafe_allow_html=True)
else:
  
    st.markdown("<h1 style='text-align:center;'>Calculadora de Diárias - IPAM</h1>", unsafe_allow_html=True)
    st.warning(f"Arquivo de logo não encontrado: {LOGO_FILENAME}. Coloque o arquivo na mesma pasta do app ou ajuste o nome.")


@st.cache_data
def carregar_dados():
    arquivo = EXCEL_FILE

    if not os.path.exists(arquivo):
        st.error(f"Arquivo Excel não encontrado: {arquivo}")
        st.stop()

    base_municipio = pd.read_excel(arquivo, sheet_name="Base Municipio")
    base_diarias = pd.read_excel(arquivo, sheet_name="Base Diárias")

    # Normaliza nomes de colunas
    base_municipio.columns = base_municipio.columns.str.strip().str.lower()
    base_diarias.columns = base_diarias.columns.str.strip()

    # Detecta nomes das colunas automaticamente
    colunas_municipio = base_municipio.columns.tolist()
    col_cidade = next((c for c in colunas_municipio if "cid" in c or "muni" in c), None)
    col_uf = next((c for c in colunas_municipio if c in ["uf", "estado"]), None)

    if not col_cidade or not col_uf:
        st.error("❌ As colunas de cidade ou UF não foram encontradas na aba 'Base Municipio'.")
        st.stop()

    return base_municipio, base_diarias, col_cidade, col_uf


# Crregamento de dados
base_municipio, base_diarias, col_cidade, col_uf = carregar_dados()

# =Sessão
if "diarias" not in st.session_state:
    st.session_state.diarias = []

# Formulario
with st.form("form_diarias"):
    st.subheader("Destino")

    cidade_nome = st.text_input("Digite o nome da cidade de destino:").strip()

    cidades_filtradas = base_municipio[
        base_municipio[col_cidade].astype(str).str.contains(cidade_nome, case=False, na=False)
    ]

    cidade_escolhida = ""
    uf = ""
    tipos_diaria = []

    if not cidades_filtradas.empty:
        cidade_escolhida = st.selectbox(
            "Selecione a cidade correspondente:",
            cidades_filtradas[col_cidade].unique(),
        )

        uf = cidades_filtradas.loc[
            cidades_filtradas[col_cidade] == cidade_escolhida, col_uf
        ].values[0]
    else:
        st.warning("Digite o nome de uma cidade válida para continuar.")

    st.text_input("UF (Estado):", uf, disabled=True)

    # Tipos de Diária 
    if cidade_escolhida:
        cidade_lower = cidade_escolhida.lower()

        if any(x in cidade_lower for x in ["brasilia", "rio branco", "manaus", "são paulo", "rio de janeiro"]):
            tipos_diaria = base_diarias[base_diarias["Tipo de Diária"].str.contains("Capitais", case=False)]["Tipo de Diária"].tolist()
        elif "comunidade" in cidade_lower or "tradicional" in cidade_lower:
            tipos_diaria = base_diarias[base_diarias["Tipo de Diária"].str.contains("Comunidades", case=False)]["Tipo de Diária"].tolist()
        elif "ater" in cidade_lower or "alter" in cidade_lower:
            tipos_diaria = base_diarias[base_diarias["Tipo de Diária"].str.contains("ATER", case=False)]["Tipo de Diária"].tolist()
        else:
            tipos_diaria = base_diarias[base_diarias["Tipo de Diária"].str.contains("Interior", case=False)]["Tipo de Diária"].tolist()

    tipo_diaria = st.selectbox("Tipo de Diária:", ["Selecione..."] + tipos_diaria)

    valor_diaria = 0.0
    if tipo_diaria != "Selecione...":
        valor_encontrado = base_diarias.loc[
            base_diarias["Tipo de Diária"] == tipo_diaria, "Valor"
        ]
        if not valor_encontrado.empty:
            valor_diaria = float(valor_encontrado.values[0])

    st.number_input("Valor da Diária (R$):", value=valor_diaria, format="%.2f", disabled=True)

    num_dias = st.number_input("Número de dias:", min_value=1, step=1)

    salvar = st.form_submit_button("💾 Salvar diária")

    if salvar:
        if cidade_escolhida and tipo_diaria != "Selecione..." and valor_diaria > 0:
            total = valor_diaria * num_dias
            st.session_state.diarias.append({
                "Cidade": cidade_escolhida,
                "Estado": uf,
                "Tipo de Diária": tipo_diaria,
                "Valor Unitário": valor_diaria,
                "Dias": num_dias,
                "Total": total
            })
            st.success("✅ Diária salva com sucesso!")
        else:
            st.warning("⚠️ Selecione uma cidade e um tipo de diária válido.")


#  Todas as diárias salvas
if st.session_state.diarias:
    st.markdown("### 🧾 Resumo das Diárias Salvas")
    df = pd.DataFrame(st.session_state.diarias)
    st.dataframe(df, use_container_width=True)

    # PDF
    if st.button("📄 Gerar PDF com Resumo"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()
        story = [Paragraph("Resumo das Diárias - IPAM", styles["Title"]), Spacer(1, 12)]

        for i, d in enumerate(st.session_state.diarias, start=1):
            story.append(Paragraph(f"<b>Diária {i}</b>", styles["Heading3"]))
            for key, value in d.items():
                story.append(Paragraph(f"{key}: {value}", styles["Normal"]))
            story.append(Spacer(1, 12))

        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()

        st.download_button(
            label="⬇️ Baixar PDF",
            data=pdf,
            file_name="diarias_IPAM.pdf",
            mime="application/pdf"
        )

    # Lixeira
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.diarias.clear()
        st.warning("Todos os registros foram apagados!")
else:
    st.info("Nenhuma diária salva até o momento.")

# Rodapé fixo 
if logo_b64:
    st.markdown(
        f"""
        <style>
            .footer-fixed {{
                position: fixed;
                right: 20px;
                bottom: 20px;
                width: 500px;
                height: 150px;
                border-radius: 20%;
                background-image: url("data:image/png;base64,{logo_b64}");
                background-size: cover;
                background-position: center;
                box-shadow: 0 4px 14px rgba(0,0,0,0.35);
                z-index: 9999;
            }}
            .footer-text-fixed {{
                position: fixed;
                left: 20px;
                bottom: 36px;
                font-size: 12px;
                color: #9aa0a6;
                z-index: 9998;
            }}
            /* evita que o conteúdo fique atrás do footer em telas pequenas */
            @media (max-width: 600px) {{
                .footer-fixed {{ width: 60px; height: 60px; bottom: 12px; right: 12px; }}
                .footer-text-fixed {{ bottom: 26px; left: 8px; font-size:11px; }}
            }}
        </style>
        <div class="footer-fixed"></div>
        <div class="footer-text-fixed">© 2025 IPAM Amazônia</div>
        """,
        unsafe_allow_html=True
    )
else:
    # fallback simples 
    footer_col1, footer_col2 = st.columns([1, 8])
    with footer_col1:
        st.write("")  # espaço
    with footer_col2:
        st.markdown("<p style='font-size:12px; color: gray;'>© 2025 IPAM Amazônia</p>", unsafe_allow_html=True)
    st.warning(f"Não foi possível embutir a logo no rodapé — arquivo '{LOGO_FILENAME}' não encontrado.")
