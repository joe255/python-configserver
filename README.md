# A minimal Spring ConfigServer written in python
Only a subset of features are included in this implementation.
- ```/{application}/{profile}/{label}``` - endpoint
- ```/{application}/{profile}``` - endpoint
Vault and Github are supported as source of the configuration. For github please provide GITHUBTOKEN as an environment variable.

If the configuration request comes with an x_config_token header field vault is queried and added to the config source.

This version supports multiple config profiles, to be switched depending on a prefix-profile provided as a header field: ```prefix```
## How to test
```
docker run \
    -p 8200:8200 \
    -e 'VAULT_DEV_ROOT_TOKEN_ID=token' \
    -e 'VAULT_ADDR=http://127.0.0.1:8200' \
    -e 'VAULT_TOKEN=token' \
    --network test --name vault vault
# Separate console
docker exec -it $(docker ps --format "{{.ID}}" --filter ancestor=vault) vault kv put secret/test foo=world bar=foo
docker exec -it $(docker ps --format "{{.ID}}" --filter ancestor=vault) vault kv put secret/test,dev foo=world bar=baz
docker exec -it $(docker ps --format "{{.ID}}" --filter ancestor=vault) vault kv put secret/test,default foo=world2 bar=baz
docker exec -it $(docker ps --format "{{.ID}}" --filter ancestor=vault) vault kv put secret/application machester=united
docker exec -it $(docker ps --format "{{.ID}}" --filter ancestor=vault) vault kv put secret/application,dev machester=closed
docker exec -it $(docker ps --format "{{.ID}}" --filter ancestor=vault) vault secrets enable -path baz -version=2 kv
docker exec -it $(docker ps --format "{{.ID}}" --filter ancestor=vault) vault kv put baz/test josef=asd

docker run -it --name=spring-cloud-config-server \
      -p 8888:8888 \
      -v $(pwd)/springconfig:/config \
      -e 'LOGGING_LEVEL_WEB=TRACE' \
      --network test --name configserver hyness/spring-cloud-config-server

cd testspring
export SPRING_CONFIG_IMPORT=configserver:http://localhost:8000
mvn clean spring-boot:run clean
export SPRING_CONFIG_IMPORT=configserver:http://localhost:8888
mvn clean spring-boot:run clean
cd ..
```
run ```python -m unittest```

To run the application run: ```uvicorn configserver:app --reload```
### Integration Testing
To compare different outcomes of this configserver and an actual spring configserver add github 
## to run 
```docker build . -t python-configserver```
```docker run -p8000 -v$(pwd)/configserver.yaml:/configserver.yaml python-configserver```