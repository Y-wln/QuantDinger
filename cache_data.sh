#!/bin/bash
TOKEN=$(sudo docker exec hermes-backend cat /app/data/mercu_live_token.txt)
curl -s -o /tmp/test_anomalies.json -H "Authorization: Bearer $TOKEN" "https://cryptosniper-epic.zeabur.app/api/radar/anomaly-v4?limit=100" --max-time 20
sudo cp /tmp/test_anomalies.json /var/lib/docker/volumes/quantdinger_backend_data/_data/mercu_anomalies.json
curl -s -o /tmp/test_momentum.json -H "Authorization: Bearer $TOKEN" "https://cryptosniper-epic.zeabur.app/api/radar/momentum?window=15m" --max-time 20
sudo cp /tmp/test_momentum.json /var/lib/docker/volumes/quantdinger_backend_data/_data/mercu_momentum.json
curl -s -o /tmp/test_surge.json -H "Authorization: Bearer $TOKEN" "https://cryptosniper-epic.zeabur.app/api/radar/surge?limit=20" --max-time 20
sudo cp /tmp/test_surge.json /var/lib/docker/volumes/quantdinger_backend_data/_data/mercu_surge.json
echo "Done"
ls -la /var/lib/docker/volumes/quantdinger_backend_data/_data/mercu_*.json
