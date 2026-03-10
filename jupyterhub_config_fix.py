# Load NOMAD's default configuration
exec(open('/opt/venv/lib/python3.12/site-packages/nomad/jupyterhub_config.py').read())

# FIX: The container name is too long for Docker DNS (63 char limit)
# We need to use IP address but must wait for network setup to complete

from nomad import config
import time

network_name = config.north.docker_network

# Use IP address (hostname too long for DNS)
c.DockerSpawner.use_internal_hostname = False
c.DockerSpawnerWithWindowsFixes.use_internal_hostname = False
c.DockerSpawner.use_internal_ip = True
c.DockerSpawnerWithWindowsFixes.use_internal_ip = True

# Set the network name explicitly
c.DockerSpawner.network_name = network_name
c.DockerSpawnerWithWindowsFixes.network_name = network_name

# CRITICAL: Don't remove containers on failure so we can debug
c.DockerSpawner.remove = False
c.DockerSpawnerWithWindowsFixes.remove = False

# Override get_ip_and_port to wait for IP assignment
from dockerspawner import DockerSpawner

original_get_ip_and_port = DockerSpawner.get_ip_and_port

async def get_ip_and_port_with_wait(self):
    """Wait for container network IP to be assigned"""
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            ip, port = await original_get_ip_and_port(self)
            if ip and ip != '':
                self.log.info(f"Got IP {ip} on attempt {attempt + 1}")
                return ip, port
            else:
                self.log.warning(f"IP empty on attempt {attempt + 1}, waiting...")
                await self.async_sleep(1)
        except Exception as e:
            if attempt < max_attempts - 1:
                self.log.warning(f"Error getting IP (attempt {attempt + 1}): {e}")
                await self.async_sleep(1)
            else:
                raise
    
    raise RuntimeError(f"Failed to get container IP after {max_attempts} attempts")

# Import async sleep helper
import asyncio
DockerSpawner.async_sleep = lambda self, seconds: asyncio.sleep(seconds)

# Apply the fix
DockerSpawner.get_ip_and_port = get_ip_and_port_with_wait
c.JupyterHub.spawner_class.__bases__[0].get_ip_and_port = get_ip_and_port_with_wait

print("=" * 80)
print(f"JUPYTERHUB CONFIG FIX LOADED")
print(f"  network_name = {network_name}")
print(f"  use_internal_ip = True (with wait for IP assignment)")
print("=" * 80)
