package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.EnvironmentMonitorPoint;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface EnvironmentMonitorPointRepository extends JpaRepository<EnvironmentMonitorPoint, Long> {

    List<EnvironmentMonitorPoint> findByPointNameContaining(String pointName);

    List<EnvironmentMonitorPoint> findByLocationContaining(String location);

    List<EnvironmentMonitorPoint> findByStatus(String status);

    List<EnvironmentMonitorPoint> findByMonitorType(String monitorType);
}
