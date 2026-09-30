package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.TrafficRoadSection;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TrafficRoadSectionRepository extends JpaRepository<TrafficRoadSection, Long> {

    List<TrafficRoadSection> findByRoadNameContaining(String roadName);

    List<TrafficRoadSection> findByRoadType(String roadType);

    List<TrafficRoadSection> findByStatus(String status);
}
