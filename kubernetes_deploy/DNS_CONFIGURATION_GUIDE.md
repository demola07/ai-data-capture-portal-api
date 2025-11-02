# DNS Configuration Guide for AWS Load Balancer

Quick reference guide for configuring DNS records for your domain with AWS Network Load Balancer.

## 🎯 Quick Answer

**For your self-managed cluster with manual AWS NLB:**

| DNS Provider | Root Domain Record | www Subdomain |
|--------------|-------------------|---------------|
| **AWS Route53** | **A (ALIAS)** → NLB | **CNAME** → root domain |
| **Cloudflare** | **CNAME** → NLB (flattened) | **CNAME** → root domain |
| **GoDaddy/Namecheap** | **A** → Resolved IPs | **CNAME** → root domain |

---

## 📋 Step-by-Step Configuration

### Step 1: Get Your NLB DNS Name

```bash
# From AWS Console
# EC2 → Load Balancers → Your NLB → DNS name
# Example: ai-data-capture-nlb-1234567890.elb.us-east-1.amazonaws.com

# Or via CLI
aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

Save this DNS name - you'll need it for configuration.

---

## 🔧 Configuration by DNS Provider

### Option 1: AWS Route53 (RECOMMENDED)

**Why Route53?**
- ✅ ALIAS records (no extra cost)
- ✅ Automatic IP updates
- ✅ Better performance
- ✅ Health checks integration

#### Using AWS Console

1. **Go to Route53:**
   - Navigate to **Route53 → Hosted Zones**
   - Click on **apidatacapture.store**

2. **Create Root Domain Record:**
   - Click **Create record**
   - **Record name:** Leave empty (for root domain)
   - **Record type:** A
   - **Toggle Alias:** ON
   - **Route traffic to:** Alias to Network Load Balancer
   - **Region:** Select your NLB region (e.g., us-east-1)
   - **Load balancer:** Select your NLB from dropdown
   - Click **Create records**

3. **Create www Subdomain:**
   - Click **Create record**
   - **Record name:** www
   - **Record type:** CNAME
   - **Value:** apidatacapture.store
   - **TTL:** 300
   - Click **Create records**

#### Using AWS CLI

```bash
# Get hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='apidatacapture.store.'].Id" \
  --output text | cut -d'/' -f3)

# Get NLB details
NLB_DNS=$(aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

NLB_HOSTED_ZONE=$(aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].CanonicalHostedZoneId' \
  --output text)

# Create ALIAS record for root domain
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "apidatacapture.store",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "'$NLB_HOSTED_ZONE'",
          "DNSName": "'$NLB_DNS'",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'

# Create CNAME for www subdomain
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "www.apidatacapture.store",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "apidatacapture.store"}]
      }
    }]
  }'
```

**Result:**
```
apidatacapture.store     A (ALIAS)  → NLB
www.apidatacapture.store CNAME      → apidatacapture.store
```

---

### Option 2: Cloudflare

**Why Cloudflare?**
- ✅ CNAME flattening (works for root domain)
- ✅ Free DDoS protection
- ✅ CDN capabilities
- ✅ Analytics

#### Configuration Steps

1. **Log in to Cloudflare Dashboard**
2. **Select your domain:** apidatacapture.store
3. **Go to DNS → Records**

4. **Create Root Domain Record:**
   - Click **Add record**
   - **Type:** CNAME
   - **Name:** @ (or apidatacapture.store)
   - **Target:** `<NLB_DNS>` (paste your NLB DNS)
   - **Proxy status:** Proxied (Orange cloud) ✅
   - **TTL:** Auto
   - Click **Save**

5. **Create www Subdomain:**
   - Click **Add record**
   - **Type:** CNAME
   - **Name:** www
   - **Target:** apidatacapture.store
   - **Proxy status:** Proxied (Orange cloud) ✅
   - **TTL:** Auto
   - Click **Save**

**Result:**
```
apidatacapture.store     CNAME (flattened)  → NLB
www.apidatacapture.store CNAME              → apidatacapture.store
```

**Note:** Cloudflare automatically flattens the CNAME for the root domain.

---

### Option 3: GoDaddy

**Limitation:** GoDaddy doesn't support CNAME for root domain.

#### Configuration Steps

1. **Resolve NLB to IP addresses:**
   ```bash
   dig +short <NLB_DNS>
   # Example output:
   # 54.123.45.67
   # 54.123.45.68
   ```

2. **Log in to GoDaddy**
3. **Go to:** My Products → DNS → Manage DNS
4. **Select domain:** apidatacapture.store

5. **Create A Records for Root Domain:**
   
   For each IP address from step 1:
   - Click **Add**
   - **Type:** A
   - **Name:** @ (for root domain)
   - **Value:** 54.123.45.67 (first IP)
   - **TTL:** 600 seconds
   - Click **Save**
   
   Repeat for second IP:
   - **Type:** A
   - **Name:** @
   - **Value:** 54.123.45.68 (second IP)
   - **TTL:** 600 seconds
   - Click **Save**

6. **Create CNAME for www:**
   - Click **Add**
   - **Type:** CNAME
   - **Name:** www
   - **Value:** apidatacapture.store
   - **TTL:** 600 seconds
   - Click **Save**

**Result:**
```
apidatacapture.store     A  → 54.123.45.67
apidatacapture.store     A  → 54.123.45.68
www.apidatacapture.store CNAME → apidatacapture.store
```

**⚠️ Warning:** NLB IPs can change. You may need to update A records if AWS changes the IPs.

---

### Option 4: Namecheap

Similar to GoDaddy - use A records with resolved IPs.

#### Configuration Steps

1. **Resolve NLB to IPs:**
   ```bash
   dig +short <NLB_DNS>
   ```

2. **Log in to Namecheap**
3. **Go to:** Domain List → Manage → Advanced DNS

4. **Create A Records:**
   - Click **Add New Record**
   - **Type:** A Record
   - **Host:** @ (for root)
   - **Value:** 54.123.45.67
   - **TTL:** 5 min
   - Click **Save**
   
   Repeat for second IP

5. **Create CNAME for www:**
   - Click **Add New Record**
   - **Type:** CNAME Record
   - **Host:** www
   - **Value:** apidatacapture.store
   - **TTL:** 5 min
   - Click **Save**

---

## ✅ Verification

After configuring DNS, verify it's working:

### Check DNS Resolution

```bash
# Check root domain
dig apidatacapture.store +short

# Check www subdomain
dig www.apidatacapture.store +short

# Check from different DNS servers
dig @8.8.8.8 apidatacapture.store +short  # Google DNS
dig @1.1.1.1 apidatacapture.store +short  # Cloudflare DNS
dig @8.8.4.4 apidatacapture.store +short  # Google DNS (alternate)
```

### Check Global Propagation

Visit: https://www.whatsmydns.net/#A/apidatacapture.store

This shows DNS propagation status worldwide.

### Test HTTP/HTTPS

```bash
# Test HTTP (should work immediately after DNS propagates)
curl -I http://apidatacapture.store

# Test HTTPS (after certificate is issued)
curl -I https://apidatacapture.store

# Test www subdomain
curl -I http://www.apidatacapture.store
```

---

## ⏱️ DNS Propagation Time

| TTL Setting | Typical Propagation Time |
|-------------|-------------------------|
| 60 seconds | 5-15 minutes |
| 300 seconds (5 min) | 15-30 minutes |
| 3600 seconds (1 hour) | 1-2 hours |
| 86400 seconds (24 hours) | 24-48 hours |

**Tip:** Use low TTL (300 seconds) during initial setup for faster changes.

---

## 🔍 Troubleshooting

### Issue: DNS Not Resolving

**Check:**
```bash
# Verify DNS servers
nslookup apidatacapture.store 8.8.8.8

# Check if record exists
dig apidatacapture.store ANY
```

**Solutions:**
- Wait longer (DNS can take up to 48 hours)
- Clear local DNS cache: `sudo dscacheutil -flushcache` (Mac)
- Try different DNS server
- Verify record was created correctly in DNS provider

### Issue: Certificate Not Issuing

**Cause:** Let's Encrypt can't reach your domain

**Check:**
```bash
# Test if domain resolves to NLB
dig apidatacapture.store +short

# Test if HTTP is accessible
curl http://apidatacapture.store/.well-known/acme-challenge/test
```

**Solutions:**
- Ensure DNS points to NLB
- Verify NLB is active and healthy
- Check security groups allow port 80
- Wait for DNS to fully propagate

### Issue: Wrong IP Returned

**Check:**
```bash
# See what IP your domain resolves to
dig apidatacapture.store +short

# Compare with NLB IPs
dig <NLB_DNS> +short
```

**Solutions:**
- Update DNS records
- Clear DNS cache
- Wait for propagation

---

## 📊 Comparison Summary

| Feature | Route53 ALIAS | Cloudflare CNAME | A Records |
|---------|---------------|------------------|-----------|
| **Root domain support** | ✅ Native | ✅ Flattened | ✅ Yes |
| **Auto IP updates** | ✅ Yes | ✅ Yes | ❌ Manual |
| **Cost** | Free | Free | Free |
| **Setup complexity** | Easy | Easy | Medium |
| **Maintenance** | None | None | Manual updates |
| **Best for** | AWS users | Everyone | Fallback |

---

## 🎯 Recommendations

### Best Choice: AWS Route53
- Use ALIAS records
- No maintenance needed
- Best performance
- Automatic IP updates

### Good Alternative: Cloudflare
- CNAME flattening works well
- Free DDoS protection
- Good global CDN

### Fallback: A Records
- Works with any provider
- Requires manual IP updates
- Use only if ALIAS/CNAME not available

---

## 📝 Quick Reference

### Your Configuration

```
Domain: apidatacapture.store
NLB DNS: <your-nlb-dns>.elb.<region>.amazonaws.com

Required Records:
1. Root domain → NLB (ALIAS or CNAME or A)
2. www subdomain → Root domain (CNAME)
```

### Verification Commands

```bash
# Check DNS
dig apidatacapture.store +short
dig www.apidatacapture.store +short

# Test access
curl -I http://apidatacapture.store
curl -I https://apidatacapture.store

# Check certificate
echo | openssl s_client -servername apidatacapture.store -connect apidatacapture.store:443 2>/dev/null | openssl x509 -noout -dates
```

---

## 🆘 Need Help?

If DNS isn't working after 1 hour:

1. **Verify record creation** in your DNS provider
2. **Check NLB is active** in AWS Console
3. **Test NLB directly:** `curl -I http://<NLB_DNS>`
4. **Check propagation:** https://www.whatsmydns.net
5. **Review security groups** - ensure port 80/443 allowed

**Common mistakes:**
- ❌ Using CNAME for root domain (non-Route53)
- ❌ Wrong NLB DNS name
- ❌ Typo in domain name
- ❌ Not waiting for propagation
- ❌ Security group blocking traffic
