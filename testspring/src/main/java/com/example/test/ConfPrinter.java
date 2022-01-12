package com.example.test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;
import javax.annotation.PostConstruct;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.EnumerablePropertySource;
import org.springframework.core.env.PropertySource;
import org.springframework.stereotype.Component;

@Component
public class ConfPrinter {
    private static final Logger log = LoggerFactory.getLogger(ConfPrinter.class);

    @Autowired
    private ConfigurableEnvironment environment;
    @Value("${spring.config.import}")
    private String fileName;

    @PostConstruct
    public void printProperties() throws IOException {
        String f = fileName.split(":")[3] + ".log";
        if (Files.exists(Paths.get(f)))
            Files.delete(Paths.get(f));
        List<String> lines = new ArrayList<>();
        for (EnumerablePropertySource propertySource : findPropertiesPropertySources()) {
            log.info("******* " + propertySource.getName() + " *******");
            String[] propertyNames = propertySource.getPropertyNames();
            Arrays.sort(propertyNames);
            for (String propertyName : propertyNames) {
                String resolvedProperty = environment.getProperty(propertyName);
                String sourceProperty = propertySource.getProperty(propertyName).toString();
                if (resolvedProperty.equals(sourceProperty)) {
                    log.info("{}={}", propertyName, resolvedProperty);
                    if (!propertySource.getName().equals("systemProperties")
                            && !propertySource.getName().equals("systemEnvironment")
                            && !propertyName.equals("spring.cloud.client.hostname"))
                        lines.add((propertyName + "=" + resolvedProperty + "\n"));
                } else {
                    log.info("{}={} OVERRIDDEN to {}", propertyName, sourceProperty, resolvedProperty);
                }
            }
        }
        String text = lines.stream().sorted().reduce((a, b) -> a + b).get();
        Files.write(Paths.get(f), text.getBytes());
        System.out.println(fileName);
    }

    private List<EnumerablePropertySource> findPropertiesPropertySources() {
        List<EnumerablePropertySource> propertiesPropertySources = new LinkedList<>();
        for (PropertySource<?> propertySource : environment.getPropertySources()) {
            if (propertySource instanceof EnumerablePropertySource) {
                propertiesPropertySources.add((EnumerablePropertySource) propertySource);
            }
        }
        return propertiesPropertySources;
    }
}