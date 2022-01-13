import pandas as pd
import requests
import json
import os
from flask import Flask, request, Response

# telegram bot token
TOKEN = os.environ.get('TOKEN_BOT') # return token value


def send_message(chat_id, text):
    url = 'https://api.telegram.org/bot{}/'.format(TOKEN)
    url = url + 'sendMessage?chat_id={}'.format(chat_id)

    response = requests.post(url, json={'text':text})
    print('Status Code {}'.format(response.status_code))

    return None


def load_dataset(store_id):
# Carregando dados de teste
    df10 = pd.read_csv('test.csv')

    df_store_raw = pd.read_csv('store.csv')

    # merge test dataset + store
    df_test = pd.merge(df10, df_store_raw, how='left', on='Store')

    # Escolhendo loja para previsão - reduz tempo de execução
    df_test = df_test[df_test['Store'] == store_id]

    # Se existir a loja informada:
    if not df_test.empty:
        # Removendo dias nos quais a loja está fechada
        df_test = df_test[df_test['Open'] != 0]
        df_test = df_test[~df_test['Open'].isnull()]

        # Removendo a coluna 'Id'
        df_test = df_test.drop('Id', axis=1)

        # Converter dataframe para json (formato comum de comunicação entre sistemas)
        data = json.dumps(df_test.to_dict(orient='records')) # uma lista de json

    else:
        data = 'error'
    
    return data


def predict(data):
    # API call
    url = 'https://rossman-sales-forecasts.herokuapp.com/rossman/predict'
    header = {'Content-type':'application/json'}
    data = data

    response = requests.post(url, data=data, headers=header)
    print('Status Code {}'.format(response.status_code))

    # Convertendo json resposta para dataframe
    d1 = pd.DataFrame(response.json(), columns=response.json()[0].keys())

    return d1


def parse_message(message):
    chat_id = message['message']['chat']['id']
    store_id = message['message']['text']
    
    store_id = store_id.replace('/', '') # substitui '/' por vazio na mensagem digitada pelo usuário.

    try:
        store_id = int(store_id)

    except ValueError:    

        if store_id == 'start':       
            msg = 'Olá! informe o número da loja que você deseja ver a previsão de faturamento.'
            send_message(chat_id, msg)
        
        else:
            send_message(chat_id, 'Wrong Store ID')
        
        store_id = 'error'

    return chat_id, store_id

# api initialize
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
  
    if request.method == 'POST':
        message = request.get_json()

        chat_id, store_id = parse_message(message)

        if store_id != 'error':
            # loading data
            data = load_dataset(store_id)

            if data != 'error':
                # prediction
                d1 = predict(data)

                # calculation
                # Exibindo previsões por lojas
                d2 = d1[['store', 'prediction']].groupby('store').sum().reset_index()

                # send message
                msg = 'Loja n. {} vai vender R${:,.2f} nas próximas 06 semanas'.format(
                        d2['store'].values[0],
                        d2['prediction'].values[0])
                
                send_message(chat_id, msg)
                return Response('Ok', status=200)
            else:
                send_message(chat_id, 'Store not Available')
                return Response('Ok', status=200)
        else:
            return Response('Ok', status=200)

    else:
        return '<h1> Rossman Telegram Bot </h1>'

if __name__=='__main__':
    port = os.environ.get('PORT',5000)
    app.run(host='0.0.0.0', port=port)