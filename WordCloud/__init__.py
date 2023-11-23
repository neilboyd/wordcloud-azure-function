import logging
import io
import os
from datetime import datetime, timedelta
import azure.functions as func
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from azure.storage.blob import ContainerClient, ContentSettings, BlobSasPermissions, generate_blob_sas


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    height = req.params.get("height")
    width = req.params.get("width")
    dpi = req.params.get("dpi")
    words = req.params.get("words")
    logging.info(f"from params: height: {height}, width: {width}, dpi:{ dpi}, words: {words}")

    try:
        req_body = req.get_json()
    except ValueError:
        logging.info("no body")
        pass
    else:
      if "height" in req_body: height = req_body["height"] 
      if "width" in req_body: width = req_body["width"] 
      if "dpi" in req_body: dpi = req_body["dpi"] 
      if "words" in req_body: words = req_body["words"] 
      logging.info(f"from body: height: {height}, width: {width}, dpi:{ dpi}, words: {words}")

    if not words:
        return func.HttpResponse("No words", status_code=400)

    height = int(height) if height else 4
    width = int(width) if width else 4
    dpi = int(dpi) if dpi else 100
    logging.info(f"finally: height: {height}, width: {width}, dpi:{ dpi}, words: {words}")

    tuple = (words, height, width, dpi)
    params_hash = abs(hash(tuple))

    logging.info(f"hash: {params_hash}")
    connection_string = os.environ["AzureWebJobsStorage"]
    logging.info(f"connection string: {connection_string}")
    now = datetime.utcnow()
    container_name = now.strftime("%Y%m")
    logging.info(f"container: {container_name}")

    # prevent excessive logging
    logging.getLogger('azure.core').setLevel(logging.WARNING)

    container = ContainerClient.from_connection_string(
        conn_str=connection_string, container_name=container_name)
    if not container.exists():
        logging.info(f"create container: {container_name}")
        container.create_container()

    blob_name = f"{params_hash}.png"
    logging.info(f"blob name: {blob_name}")
    blob = container.get_blob_client(blob=blob_name)

    if not blob.exists():
        logging.info(f"create wordcloud blob: {blob_name}")

        # https://matplotlib.org/stable/tutorials/colors/colormaps.html
        color = "lightblue"
        colormap = "winter"
        wordcloud = WordCloud(width=width * dpi, height=height * dpi,
                              background_color=color, colormap=colormap)
        image = wordcloud.generate(words)

        plt.figure(figsize=(width, height))

        # hide axes https://gist.github.com/kylemcdonald/bedcc053db0e7843ef95c531957cb90f
        ax = plt.axes([0, 0, 1, 1], frameon=False)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)

        plt.imshow(image, interpolation='bilinear')

        fp = io.BytesIO()
        plt.savefig(fp)

        # save image to blob
        blob.upload_blob(fp.getvalue(),
                         content_settings=ContentSettings(content_type="image/png"))

    dict = {x[0]: x[1] for x in [
        x.split("=", maxsplit=1) for x in connection_string.split(";")]}
    logging.info(f"parsed connection string: {dict}")
    account_key = dict["AccountKey"]
    logging.info(f"account_key: {account_key}")

    sas_blob = generate_blob_sas(account_name=blob.account_name,
                                 container_name=container_name,
                                 blob_name=blob_name,
                                 account_key=account_key,
                                 permission=BlobSasPermissions(read=True),
                                 expiry=now + timedelta(hours=1))
    logging.info(f"sas_blob: {sas_blob}")
    url = blob.url + "?" + sas_blob
    logging.info(f"url: {url}")
    return func.HttpResponse(url, headers={'Location': url}, status_code=302)
