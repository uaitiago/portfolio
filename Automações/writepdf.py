from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter, PageObject
import pandas as pd
import os

# Função para adicionar texto ao PDF
def preencher_pdf(dados_aluno, modelo_pdf, output_pdf):
    # Verificar se o arquivo PDF do modelo existe
    if not os.path.exists(modelo_pdf):
        print(f"Arquivo modelo PDF não encontrado: {modelo_pdf}")
        return

    # Criação de um PDF temporário com as informações preenchidas
    temp_pdf = "temp.pdf"
    c = canvas.Canvas(temp_pdf)
    c.setFont("Times-Roman", 9)

    # Preencher os campos com as informações do aluno (x,y) -> (y,x)
    c.drawString(100, 657, f"{dados_aluno['Nome']}")
    c.drawString(490, 657, f" {dados_aluno['Idade']}")
    c.drawString(520, 657, f"{dados_aluno['Sexo']}")
    c.drawString(155, 640, f"     {dados_aluno['DatadeNascimento']}")
    c.drawString(280, 640, f" {dados_aluno['CPF']}")
    c.drawString(125, 620, f" {dados_aluno['NomedaMae']}")
    c.drawString(400, 620, f" {dados_aluno['Fone']}")
    c.drawString(100, 605, f" {dados_aluno['Endereço']}")
    c.drawString(100, 585, f" {dados_aluno['Cidade']}")
    c.drawString(430, 585, f" {dados_aluno['CEP']}")
    c.drawString(550, 750, f" {dados_aluno['turma']}")
    c.drawString(370, 585, f" GO")

    # Salvar o PDF temporário
    c.save()

    # Mesclar o modelo PDF com o PDF preenchido
    try:
        with open(modelo_pdf, "rb") as modelo_file:
            modelo_pdf_reader = PdfReader(modelo_file)
            modelo_page = modelo_pdf_reader.pages[0]

            # Carregar o PDF gerado com informações preenchidas
            preenchido_pdf_reader = PdfReader(temp_pdf)
            preenchido_page = preenchido_pdf_reader.pages[0]

            # Criar uma nova página com o mesmo tamanho do modelo
            new_page = PageObject.create_blank_page(
                width=modelo_page.mediabox.width, height=modelo_page.mediabox.height
            )

            # Mesclar a página preenchida com o modelo
            new_page.merge_page(modelo_page)
            new_page.merge_page(preenchido_page)

            # Salvar o novo PDF
            writer = PdfWriter()
            writer.add_page(new_page)

            with open(output_pdf, "wb") as final_pdf:
                writer.write(final_pdf)

    finally:
        # Remover o PDF temporário
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)

# Caminho para o CSV e modelo PDF
file_path = r'C:\Users\tiago Antonio\Desktop\dados_aluno.csv'  # Certifique-se de que o arquivo CSV existe e o caminho está correto
modelo_pdf = r'C:\Users\tiago Antonio\Desktop\modelo_pdf.pdf'  # Certifique-se de que o arquivo PDF existe e o caminho está correto

# Verificar se o arquivo CSV existe
if not os.path.exists(file_path):
    print(f"Arquivo CSV não encontrado: {file_path}")
else:
    # Ler os dados do CSV
    dados_alunos = pd.read_csv(file_path)

    # Diretório de saída para os PDFs gerados
    diretorio_saida = r'C:\Users\tiago Antonio\Desktop\PDFs_Gerados'
    if not os.path.exists(diretorio_saida):
        os.makedirs(diretorio_saida)

    # Garantir que os valores na coluna 'Aluno' sejam strings
    dados_alunos['Aluno'] = dados_alunos['Nome'].fillna('Sem_Nome').astype(str)
    dados_alunos['turma'] = dados_alunos['Turma'].fillna('Sem_Turma').astype(str)

    # Gerar os PDFs para cada aluno
    for _, aluno in dados_alunos.iterrows():
        # Usar replace apenas após garantir que o valor é uma string
        nome_aluno = aluno['Aluno'].replace(' ', '_')
        turma = aluno['turma'].replace(' ', '_')
        output_pdf = os.path.join(diretorio_saida, f"{turma}_termo_de_entrega_{nome_aluno}.pdf")
        preencher_pdf(aluno, modelo_pdf, output_pdf)

    print("PDFs preenchidos e salvos com sucesso!")
