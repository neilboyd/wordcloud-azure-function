import logging
import os
from datetime import datetime, timedelta
import azure.functions as func
from azure.storage.blob import ContainerClient, ContentSettings, BlobSasPermissions, generate_blob_sas


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    words = req.params.get("words")
    logging.info(f"words: {words}")
    if not words:
        return func.HttpResponse("No words", status_code=400)

    logging.info(f"hash: {hash(words)}")
    connection_string = os.environ["AzureWebJobsStorage"]
    logging.info(f"connection string: {connection_string}")
    now = datetime.utcnow()
    container_name = now.strftime("%Y%m")
    logging.info(f"container: {container_name}")

    container = ContainerClient.from_connection_string(
        conn_str=connection_string, container_name=container_name)
    if not container.exists():
        logging.info(f"create container: {container_name}")
        container.create_container()

    blob_name = f"{abs(hash(words))}.txt"  # TODO png
    logging.info(f"blob name: {blob_name}")
    blob = container.get_blob_client(blob=blob_name)

    if not blob.exists():
        logging.info(f"create blob: {blob_name}")
        # TODO the whole word cloud thing
        # for now just this
        blob.upload_blob(words, content_settings=ContentSettings(
            content_type='text/plain'))

    dict = {x[0]: x[1] for x in [x.split("=", maxsplit=1) for x in connection_string.split(";")]}
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
