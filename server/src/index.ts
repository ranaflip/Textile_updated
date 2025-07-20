import express from 'express';
import mongoose from 'mongoose';
import { Queue } from 'bullmq';
import { createBullBoard } from '@bull-board/api';
import { BullMQAdapter } from '@bull-board/api/bullMQAdapter';
import { ExpressAdapter } from '@bull-board/express';
import dotenv from 'dotenv';
import linkRouter from './routes/links';
import scrapeRouter from './routes/scrapes';
import { scrapeQueue } from './workers/scraper';

dotenv.config();
const app = express();
app.use(express.json());

mongoose.connect(process.env.MONGODB_URI!);

app.use('/links', linkRouter);
app.use('/scrapes', scrapeRouter);

// optional admin UI for BullMQ
const serverAdapter = new ExpressAdapter();
createBullBoard({
  queues: [new BullMQAdapter(scrapeQueue)],
  serverAdapter,
});
serverAdapter.setBasePath('/admin');
app.use('/admin', serverAdapter.getRouter());

const port = process.env.PORT || 4000;
app.listen(port, () => console.log(`API on :${port}`));