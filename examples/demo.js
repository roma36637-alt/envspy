const port = process.env.PORT || 3000;
const db = process.env.DATABASE_URL;
const key = process.env['API_' + 'TOKEN'];

console.log('demo app started on', port, Boolean(db), Boolean(key));