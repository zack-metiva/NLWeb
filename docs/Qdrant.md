## Loading data locally

To load data locally, you'll want to use [Qdrant](https://qdrant.tech/) as your local vector database. You'll need an embedding endpoint to create data for your vector database. In this example we'll use Azure OpenAI.

1. Install `qdrant`

   Install Qdrant locally from https://github.com/qdrant/qdrant/releases. Download the package appropriate for your system. Before you start the service, keep in mind, that by default, Qdrant will create a directory `./storage` in the directory you start it from unless you change the configuration. For more configuration information see [the Qdrant configuration docs](https://qdrant.tech/documentation/guides/configuration/).
   
   On Linux, this can be invoked simply as `qdrant`, which will show the service starting on the console.

2. Configure nlweb to use qdrant, and your embedding endpoint.

   Ensure the following environment variables exist that match your LLM resource you created above in [Azure OpenAI Endpoint Creation](#azure-openai-endpoint-creation). These can be either in your .env file, or as exported variables.

   ```bash
   export AZURE_OPENAI_API_KEY="<my azure openai key>"
   export AZURE_OPENAI_ENDPOINT="<my azure openai endpoint>"
   ```

3. Ensure that your preferred endpoint is configured

   Modify the file at `./code/config/config_retrieval.yaml` and ensure that the `preferred_endpoint:` value is `qdrant_local`.

   ```yaml
   preferred_endpoint: qdrant_local
   ```

4. Pick your data source, and generate embeddings for Qdrant.

   You can load local JSON, or use an RSS feed of your choice. Replace "mysite" with a site that has rss feeds you wish to load.

   ```bash
   cd code
   python -m tools.db_load --url-list ../data/json/scifi_movies_schemas.txt scifi_movies --database qdrant_local
   ```
   You can find more data examples at [docs/db_load.md](db_load.md).

   Other methods of invoking the emdedding tool:

   ```bash
    python -m tools.db_load file.txt site_name
    python -m tools.db_load https://example.com/feed.rss site_name
    python -m tools.db_load data.csv site_name
    python -m tools.db_load --delete-site site_name
    python -m tools.db_load file.txt site_name --database qdrant_local
    python -m tools.db_load --force-recompute file.txt site_name
    python -m tools.db_load --url-list urls.txt site_name
    python -m tools.db_load --url-list https://example.com/feed_list.txt site_name
   ```

4. Test the nlweb app

   From here, you should be able to go to your locally installed nlweb app at `http://localhost:8000` and query the data you've loaded.
