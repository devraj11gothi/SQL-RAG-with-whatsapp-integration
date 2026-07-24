# Test Questions

For comparing model quality/speed (e.g. 4B vs 12B) on the Chinook chat-with-SQL app.

## Moderate (2-3 tables, single join/aggregation)

1. How many tracks are in the genre 'Metal'? — **374**
2. What is the average track length in minutes across the whole catalog? — **~6.56 minutes**
3. List the top 3 customers by total number of invoices. — **Tie: 58 of 59 customers all have exactly 7 invoices** (only 1 customer has 6). Not a useful discriminating question as-is — good test for whether the model notices/flags the tie instead of picking an arbitrary 3.
4. Which album has the most tracks? — **"Greatest Hits" (57 tracks)**, then "Minha Historia" (34), "Unplugged" (30)
5. How many invoices were billed to Germany? — **28**

## Hard (4+ tables, multiple constraints, multi-hop)

1. Which genre generates the most revenue from customers whose support rep is Steve Johnson? — **Rock ($228.69)**, then Latin ($117.81), Alternative & Punk ($88.11)
2. What is the total revenue from tracks longer than 5 minutes, broken down by media type? — **MPEG audio file: $510.84**, Protected MPEG-4 video file: $220.89, Protected AAC audio file: $54.45, Purchased AAC audio file: $1.98
3. Among customers with more than 3 invoices, which country has the highest average invoice total? — **Chile ($6.66 avg)**, then Hungary/Ireland (tied $6.52). Note: nearly every customer has >3 invoices (see M3), so this filter barely excludes anyone — weak constraint, good for testing if the model notices.
4. Which artist's tracks appear on the most playlists? — **Eugene Ormandy (7 distinct playlists)**, then several classical artists tied at 6
5. Between Rock and Jazz, which genre earned more total revenue from customers in Canada? — **Rock ($105.93) vs Jazz ($12.87) — Rock wins by a lot**

## Already tested (round 1, multi-hop set)

1. Which country's customers bought the most Jazz tracks? — USA (22)
2. Which employee's customers generated the highest total invoice revenue? — Jane Peacock (833.04)
3. What's the most purchased genre among customers supported by 'Sales Support Agent' employees? — Rock
4. Which artist has the highest total sales revenue from USA customers? — The Office (33.83, narrowly over Iron Maiden 33.66)
5. Which media type is most common among tracks bought by customers who've spent over $40 total? — not yet verified (timed out on 12B model)
