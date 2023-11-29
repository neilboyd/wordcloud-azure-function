import logging
import io
import os
from datetime import datetime, timedelta
import azure.functions as func
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from azure.storage.blob import ContainerClient, ContentSettings, BlobSasPermissions, generate_blob_sas


def main(req: func.HttpRequest) -> func.HttpResponse:

    words = req.params.get("words")
    height = req.params.get("height")
    width = req.params.get("width")
    dpi = req.params.get("dpi")
    color = req.params.get("color")
    colormap = req.params.get("colormap")

    try:
        req_body = req.get_json()
    except ValueError:
        logging.info("no body")
        pass
    else:
        if "words" in req_body:
            words = req_body["words"]
        if "height" in req_body:
            height = req_body["height"]
        if "width" in req_body:
            width = req_body["width"]
        if "dpi" in req_body:
            dpi = req_body["dpi"]
        if "color" in req_body:
            color = req_body["color"]
        if "colormap" in req_body:
            colormap = req_body["colormap"]

    if not words:
        return func.HttpResponse("No words", status_code=400)

    height = int(height) if height else 4
    width = int(width) if width else 4
    dpi = int(dpi) if dpi else 100
    if not color:
        color = "lightblue"
    if not colormap:
        colormap = "winter"

    logging.info(
        f"height: {height}, width: {width}, dpi:{dpi}, color:{color}, colormap:{colormap}, words: {words}")

    if height * width * dpi > 12 * 12 * 100:  # square foot
        return func.HttpResponse("Image size too large", status_code=400)

    tuple = (words, height, width, dpi, color, colormap)
    params_hash = abs(hash(tuple))

    connection_string = os.environ["AzureWebJobsStorage"]
    now = datetime.utcnow()
    container_name = now.strftime("%Y%m")

    # prevent excessive logging
    logging.getLogger('azure.core').setLevel(logging.WARNING)

    container = ContainerClient.from_connection_string(
        conn_str=connection_string, container_name=container_name)
    if not container.exists():
        container.create_container()

    blob_name = f"{params_hash}.png"
    blob = container.get_blob_client(blob=blob_name)

    if not blob.exists():
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
    account_key = dict["AccountKey"]

    sas_blob = generate_blob_sas(account_name=blob.account_name,
                                 container_name=container_name,
                                 blob_name=blob_name,
                                 account_key=account_key,
                                 permission=BlobSasPermissions(read=True),
                                 expiry=now + timedelta(weeks=4))
    url = blob.url + "?" + sas_blob
    logging.info(f"redirect to: {url}")
    return func.HttpResponse(url, headers={'Location': url}, status_code=302)
