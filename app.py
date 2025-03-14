import json
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd

# Criando o app Flask
app = Flask(__name__)
CORS(app)

# Caminho do arquivo de produtos
ARQUIVO_PRODUTOS = "produtos.json"  # Ajuste conforme necessário para seu ambiente (ex.: /tmp/produtos.json)

# Função para carregar os produtos
def carregar_produtos():
    try:
        if os.path.exists(ARQUIVO_PRODUTOS):
            with open(ARQUIVO_PRODUTOS, "r", encoding="utf-8") as file:
                return json.load(file)
        else:
            return []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Função para salvar produtos
def salvar_produtos(produtos):
    try:
        with open(ARQUIVO_PRODUTOS, "w", encoding="utf-8") as file:
            json.dump(produtos, file, indent=4, ensure_ascii=False)
    except Exception as e:
        return jsonify({"erro": f"Erro ao salvar os produtos: {str(e)}"}), 500

produtos = carregar_produtos()

def validar_dados_produto(produto):
    return bool(produto.get('descricao_produto') and produto.get('cod_barras'))

@app.route('/')
def rota_padrao():
    return jsonify({"mensagem": "API de Produtos funcionando! Consulte /api/produtos"}), 200

@app.route('/api/produtos', methods=['GET'])
def listar_produtos():
    return jsonify(produtos)

@app.route('/api/produto/<cod_barras>', methods=['GET'])
def obter_produto(cod_barras):
    produto = next((p for p in produtos if str(p["cod_barras"]) == str(cod_barras)), None)
    if produto:
        return jsonify(produto)
    return jsonify({"erro": "Produto não encontrado"}), 404

@app.route('/api/produtos', methods=['POST'])
def adicionar_produto():
    novo_produto = request.get_json()
    if not validar_dados_produto(novo_produto):
        return jsonify({"erro": "Dados do produto inválidos."}), 400

    novo_produto["cod_barras"] = str(novo_produto["cod_barras"])

    if any(p["cod_barras"] == novo_produto["cod_barras"] for p in produtos):
        return jsonify({"erro": "Produto com esse código de barras já existe."}), 409

    produtos.append(novo_produto)
    salvar_produtos(produtos)
    return jsonify(novo_produto), 201

@app.route('/api/produto/<cod_barras>', methods=['PUT'])
def atualizar_produto(cod_barras):
    produto = next((p for p in produtos if str(p["cod_barras"]) == str(cod_barras)), None)
    if not produto:
        return jsonify({"erro": "Produto não encontrado"}), 404

    dados_atualizados = request.get_json()
    
    if not isinstance(dados_atualizados, dict) or not validar_dados_produto(dados_atualizados):
        return jsonify({"erro": "Dados inválidos para atualização."}), 400

    produto.update({
        "descricao_produto": dados_atualizados.get("descricao_produto", produto["descricao_produto"]),
        "imagem": dados_atualizados.get("imagem", produto.get("imagem", ""))
    })

    salvar_produtos(produtos)
    return jsonify({"mensagem": "Produto atualizado com sucesso", "produto": produto})

@app.route('/api/produto/<cod_barras>', methods=['DELETE'])
def excluir_produto(cod_barras):
    global produtos
    produtos = [p for p in produtos if str(p["cod_barras"]) != str(cod_barras)]
    salvar_produtos(produtos)
    return jsonify({"mensagem": "Produto excluído com sucesso"})

@app.route('/api/produtos', methods=['DELETE'])
def excluir_todos_produtos():
    global produtos
    produtos = []  # Limpa a lista de produtos
    salvar_produtos(produtos)
    return jsonify({"mensagem": "Todos os produtos foram excluídos com sucesso."})

@app.route('/api/importar_produtos', methods=['POST'])
def importar_produtos():
    if 'file' in request.files:
        file = request.files['file']
        
        try:
            if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
                # Processa arquivo Excel
                df = pd.read_excel(file)
                df = df.rename(columns={
                    'DESCRICAO_PRODUTO': 'descricao_produto',
                    'COD_BARRAS': 'cod_barras',
                    'IMAGEM': 'imagem'
                })
                df['imagem'] = df['imagem'].fillna("")
                lista_produtos = df.to_dict(orient='records')

            elif file.filename.endswith('.json'):
                # Processa arquivo JSON
                lista_produtos = json.load(file)
            else:
                return jsonify({"erro": "Formato de arquivo inválido. Envie um arquivo Excel ou JSON."}), 400

            produtos_importados = []
            for produto in lista_produtos:
                if validar_dados_produto(produto):
                    produto["cod_barras"] = str(produto["cod_barras"])
                    if any(p["cod_barras"] == produto["cod_barras"] for p in produtos):
                        continue
                    produtos.append(produto)
                    produtos_importados.append(produto)

            salvar_produtos(produtos)

            return jsonify({"mensagem": f"{len(produtos_importados)} produtos importados com sucesso."}), 201

        except Exception as e:
            return jsonify({"erro": f"Erro ao processar o arquivo: {str(e)}"}), 500

    elif request.is_json:
        try:
            dados_json = request.get_json()

            produtos_importados = []
            for produto in dados_json:
                if validar_dados_produto(produto):
                    produto["cod_barras"] = str(produto["cod_barras"])
                    if any(p["cod_barras"] == produto["cod_barras"] for p in produtos):
                        continue
                    produtos.append(produto)
                    produtos_importados.append(produto)

            salvar_produtos(produtos)

            return jsonify({"mensagem": f"{len(produtos_importados)} produtos importados com sucesso."}), 201

        except Exception as e:
            return jsonify({"erro": f"Erro ao processar os dados JSON: {str(e)}"}), 500

    else:
        return jsonify({"erro": "Nenhum arquivo ou dados JSON enviados."}), 400

if __name__ == '__main__':
    app.run(debug=True)
