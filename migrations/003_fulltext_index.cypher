// migrations/003_fulltext_index.cypher
// Создание fulltext индекса для keyword search

CREATE FULLTEXT INDEX episode_content IF NOT EXISTS
FOR (ep:Episode) 
ON EACH [ep.content, ep.summary]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'standard-no-stop-words'
  }
};

