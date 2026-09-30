package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.EnergyDevice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface EnergyDeviceRepository extends JpaRepository<EnergyDevice, String> {
    List<EnergyDevice> findByDeviceTypeContaining(String deviceType);
    List<EnergyDevice> findByStatus(String status);
    List<EnergyDevice> findByLocationContaining(String location);
}
