from flask import Flask, render_template, request
import os
from opensearchpy import OpenSearch
from dotenv import load_dotenv

load_dotenv()  


app = Flask(__name__)


class OpenDistroElasticsearch:
    def __init__(self):
        self.client = self.connect_server(
            os.getenv('OPENDISTROES_ADDRESS'), 
            int(os.getenv('OPENDISTROES_PORT'))
        )

    def connect_server(self, ip, port):
        hosts = [{'host': ip, 'port': port}]
        client = OpenSearch(
            hosts=hosts,
            http_auth=(os.getenv('OPENDISTROES_USERNAME'), os.getenv('OPENDISTROES_PASSWORD')),
            use_ssl=False,
            verify_certs=False,
            request_timeout=10*60
        )

        
        try:
            info = client.info()
            print("Kết nối thành công đến Open Distro for Elasticsearch")
            print(info)
        except Exception as e:
            print(f"Không thể kết nối đến Open Distro for Elasticsearch: {e}")

        return client

    def search(self, index, size, body):
        return self.client.search(index=index, size=size, body=body)


es_client = OpenDistroElasticsearch().client


def search_elasticsearch(query, index="deepb", size=20):
    body = {
        "query": {
            "match": {
                "content": query  
            }
        }
    }

    
    search_results = es_client.search(index=index, body=body, size=size)

    
    results = []
    for hit in search_results['hits']['hits']:
        source = hit['_source']
        image = None
        if 'attachments' in source:
            for attachment in source['attachments']:
                image = attachment.get('attachment_link', None)
                if image:
                    break
        results.append({
        'title': source.get('content', ''), 
        'link': source.get('link', ''),      
        'image':image,                     
        'source': source.get('source', {}).get('source_name', ''),  
        'filename': source.get('filename', 'Không có tên tệp')     
    })


    return results
def search_elasticsearch_with_body(body, index="deepb", size=200):
    try:
        response = es_client.search(index=index, body=body, size=size)
        results = []
        count = 0

        for hit in response['hits']['hits']:
            source = hit['_source']
            image = None

            if 'attachments' in source:
                for attachment in source['attachments']:
                    image = attachment.get('attachment_link', None)
                    if image:
                        break  
            if image:
                results.append({
                    'title': source.get('content', ''), 
                    'link': source.get('link', ''),      
                    'image': image,                     
                    'source': source.get('source', {}).get('source_name', ''),  
                    'filename': source.get('filename', 'Không có tên tệp')     
                })
                count += 1

            if count >= 5:
                break
        if len(results) < 5:
            return results + search_elasticsearch_with_body(body, index=index, size=size-len(results))

        return results

    except Exception as e:
        print(f"Đã xảy ra lỗi khi tìm kiếm: {e}")
        return []

@app.route('/')
def index():

    body = {
        "query": {
            "function_score": {
                "query": {
                    "match_all": {}
                },
                "functions": [
                    {
                        "random_score": {}
                    }
                ],
                "boost_mode": "replace"
            }
        },
        "size": 100
    }
    
    results = search_elasticsearch_with_body(body)
    return render_template('index.html', data=results)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('filename', '') 
    results = search_elasticsearch(query)    
    
    results = results[:20]
    return render_template('search_results.html', results=results, query=query)

# Kiểm tra nếu là script chính
if __name__ == "__main__":
    app.run(debug=True)
