git pull

docker build . --tag funpolice:latest

docker run --rm \
 --name funpolice-dev \
 --network prod \
 -v $PWD/dev_logs:/funpolice/logs \
 funpolice --debug --dev-bot
