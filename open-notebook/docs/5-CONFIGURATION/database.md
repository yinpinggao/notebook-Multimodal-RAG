# Database - SeekDB Configuration

Open Notebook uses SeekDB for its database needs. SeekDB is an MySQL-compatible database that supports full-text search and vector operations.

---

## Default Configuration

Open Notebook should work out of the box with SeekDB as long as the environment variables are correctly setup.

### DB running in the same docker compose as Open Notebook (recommended)

The example above is for when you are running SeekDB as a separate docker container, which is the method described [here](../1-INSTALLATION/docker-compose.md) (and our recommended method).

```env
OPEN_NOTEBOOK_SEEKDB_DSN=mysql://root:SeekDBRoot123%21@seekdb:2881/open_notebook_ai
OPEN_NOTEBOOK_AI_CONFIG_BACKEND=seekdb
OPEN_NOTEBOOK_SEARCH_BACKEND=seekdb
```

### DB running in the host machine and Open Notebook running in Docker

If ON is running in docker and SeekDB is on your host machine, you need to point to it.

```env
OPEN_NOTEBOOK_SEEKDB_DSN=mysql://root:SeekDBRoot123%21@host.docker.internal:2881/open_notebook_ai
OPEN_NOTEBOOK_AI_CONFIG_BACKEND=seekdb
OPEN_NOTEBOOK_SEARCH_BACKEND=seekdb
```

### Open Notebook and SeekDB are running on the same machine

If you are running both services locally or if you are using the deprecated single container setup.

```env
OPEN_NOTEBOOK_SEEKDB_DSN=mysql://root:SeekDBRoot123%21@127.0.0.1:2881/open_notebook_ai
OPEN_NOTEBOOK_AI_CONFIG_BACKEND=seekdb
OPEN_NOTEBOOK_SEARCH_BACKEND=seekdb
```

## Multiple databases

You can have multiple databases in one SeekDB instance. If you want to setup multiple open notebook deployments for different users, you don't need to deploy multiple SeekDB instances — just create a separate database for each deployment.
